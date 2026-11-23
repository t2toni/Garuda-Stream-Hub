#include "stream_native.hpp"

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <fcntl.h>
#include <unistd.h>
#include <poll.h>
#include <sys/resource.h>
#include <sys/time.h>

#include <iostream>
#include <fstream>
#include <sstream>
#include <cmath>
#include <algorithm>
#include <cstring>

namespace stream_native {

JitterCalculator::JitterCalculator(size_t window_size)
    : window_size_(window_size), jitter_estimate_(0.0), last_rtt_(-1.0) {}

void JitterCalculator::add_sample(double rtt_ms) {
    if (rtt_ms < 0.0) return;
    std::lock_guard<std::mutex> lock(mutex_);

    rtt_samples_.push_back(rtt_ms);
    if (rtt_samples_.size() > window_size_) {
        rtt_samples_.pop_front();
    }

    if (last_rtt_ >= 0.0) {
        double d = std::abs(rtt_ms - last_rtt_);
        jitter_estimate_ += (d - jitter_estimate_) / 16.0;
    } else {
        jitter_estimate_ = 0.0;
    }
    last_rtt_ = rtt_ms;
}

double JitterCalculator::get_jitter_ms() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return jitter_estimate_;
}

double JitterCalculator::get_avg_rtt_ms() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (rtt_samples_.empty()) return 0.0;
    double sum = 0.0;
    for (double val : rtt_samples_) sum += val;
    return sum / static_cast<double>(rtt_samples_.size());
}

double JitterCalculator::get_min_rtt_ms() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (rtt_samples_.empty()) return 0.0;
    return *std::min_element(rtt_samples_.begin(), rtt_samples_.end());
}

double JitterCalculator::get_max_rtt_ms() const {
    std::lock_guard<std::mutex> lock(mutex_);
    if (rtt_samples_.empty()) return 0.0;
    return *std::max_element(rtt_samples_.begin(), rtt_samples_.end());
}

int JitterCalculator::get_recommended_buffer_ms() const {
    std::lock_guard<std::mutex> lock(mutex_);
    // Minimum 15ms target buffer, scales up if jitter exceeds 5ms
    int buffer = 15 + static_cast<int>(std::round(jitter_estimate_ * 2.0));
    if (buffer < 15) buffer = 15;
    if (buffer > 100) buffer = 100;
    return buffer;
}

void JitterCalculator::reset() {
    std::lock_guard<std::mutex> lock(mutex_);
    rtt_samples_.clear();
    jitter_estimate_ = 0.0;
    last_rtt_ = -1.0;
}

double ping_host(const std::string& host, int port, int timeout_ms) {
    auto start_time = std::chrono::high_resolution_clock::now();

    struct addrinfo hints{}, *res = nullptr;
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    std::string port_str = std::to_string(port);
    if (getaddrinfo(host.c_str(), port_str.c_str(), &hints, &res) != 0 || !res) {
        return -1.0;
    }

    int sock = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (sock < 0) {
        freeaddrinfo(res);
        return -1.0;
    }

    int flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);

    int conn_res = connect(sock, res->ai_addr, res->ai_addrlen);
    freeaddrinfo(res);

    if (conn_res < 0 && errno != EINPROGRESS) {
        close(sock);
        return -1.0;
    }

    if (conn_res == 0) {
        // Immediate connection
        close(sock);
        auto end_time = std::chrono::high_resolution_clock::now();
        std::chrono::duration<double, std::milli> duration = end_time - start_time;
        return duration.count();
    }

    struct pollfd pfd;
    pfd.fd = sock;
    pfd.events = POLLOUT;

    int poll_res = poll(&pfd, 1, timeout_ms);
    if (poll_res <= 0) {
        close(sock);
        return -1.0;
    }

    int so_error = 0;
    socklen_t len = sizeof(so_error);
    getsockopt(sock, SOL_SOCKET, SO_ERROR, &so_error, &len);
    close(sock);

    if (so_error != 0) {
        return -1.0;
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> duration = end_time - start_time;
    return duration.count();
}

bool elevate_process_priority(int pid, int desired_nice, int& effective_nice, std::string& error_msg) {
    errno = 0;
    if (setpriority(PRIO_PROCESS, pid, desired_nice) != 0) {
        error_msg = std::strerror(errno);
        effective_nice = getpriority(PRIO_PROCESS, pid);
        return false;
    }

    effective_nice = getpriority(PRIO_PROCESS, pid);
    error_msg = "";
    return true;
}

ProcessStats get_process_stats(int pid) {
    ProcessStats stats;
    stats.pid = pid;
    stats.name = "";
    stats.state = "unknown";
    stats.vm_rss_kb = 0;
    stats.cpu_user_time = 0;
    stats.cpu_sys_time = 0;
    stats.nice_level = 0;
    stats.num_threads = 0;
    stats.is_running = false;

    std::string status_path = "/proc/" + std::to_string(pid) + "/status";
    std::ifstream status_file(status_path);
    if (!status_file.is_open()) {
        return stats;
    }

    stats.is_running = true;
    std::string line;
    while (std::getline(status_file, line)) {
        if (line.rfind("Name:", 0) == 0) {
            stats.name = line.substr(5);
            stats.name.erase(0, stats.name.find_first_not_of(" \t"));
        } else if (line.rfind("State:", 0) == 0) {
            stats.state = line.substr(6);
            stats.state.erase(0, stats.state.find_first_not_of(" \t"));
            size_t end = stats.state.find_first_of(" \t");
            if (end != std::string::npos) stats.state = stats.state.substr(0, end);
        } else if (line.rfind("VmRSS:", 0) == 0) {
            std::stringstream ss(line.substr(6));
            ss >> stats.vm_rss_kb;
        } else if (line.rfind("Threads:", 0) == 0) {
            std::stringstream ss(line.substr(8));
            ss >> stats.num_threads;
        }
    }

    std::string stat_path = "/proc/" + std::to_string(pid) + "/stat";
    std::ifstream stat_file(stat_path);
    if (stat_file.is_open()) {
        std::string word;
        std::vector<std::string> fields;
        while (stat_file >> word) {
            fields.push_back(word);
        }
        // fields[13] = utime, fields[14] = stime, fields[18] = priority, fields[19] = nice
        if (fields.size() >= 20) {
            try {
                stats.cpu_user_time = std::stoull(fields[13]);
                stats.cpu_sys_time = std::stoull(fields[14]);
                stats.nice_level = std::stoi(fields[18]);
            } catch (...) {}
        }
    }

    return stats;
}

} // namespace stream_native

namespace py = pybind11;

PYBIND11_MODULE(stream_native, m) {
    m.doc() = "Native C++ High-Performance Telemetry and Scheduling Engine for Stream Pipeline";

    py::class_<stream_native::ProcessStats>(m, "ProcessStats")
        .def_readonly("pid", &stream_native::ProcessStats::pid)
        .def_readonly("name", &stream_native::ProcessStats::name)
        .def_readonly("state", &stream_native::ProcessStats::state)
        .def_readonly("vm_rss_kb", &stream_native::ProcessStats::vm_rss_kb)
        .def_readonly("cpu_user_time", &stream_native::ProcessStats::cpu_user_time)
        .def_readonly("cpu_sys_time", &stream_native::ProcessStats::cpu_sys_time)
        .def_readonly("nice_level", &stream_native::ProcessStats::nice_level)
        .def_readonly("num_threads", &stream_native::ProcessStats::num_threads)
        .def_readonly("is_running", &stream_native::ProcessStats::is_running);

    py::class_<stream_native::JitterCalculator>(m, "JitterCalculator")
        .def(py::init<size_t>(), py::arg("window_size") = 30)
        .def("add_sample", &stream_native::JitterCalculator::add_sample, py::arg("rtt_ms"))
        .def("get_jitter_ms", &stream_native::JitterCalculator::get_jitter_ms)
        .def("get_avg_rtt_ms", &stream_native::JitterCalculator::get_avg_rtt_ms)
        .def("get_min_rtt_ms", &stream_native::JitterCalculator::get_min_rtt_ms)
        .def("get_max_rtt_ms", &stream_native::JitterCalculator::get_max_rtt_ms)
        .def("get_recommended_buffer_ms", &stream_native::JitterCalculator::get_recommended_buffer_ms)
        .def("reset", &stream_native::JitterCalculator::reset);

    m.def("ping_host", &stream_native::ping_host,
          py::arg("host"), py::arg("port") = 5555, py::arg("timeout_ms") = 800,
          "Measures TCP connection latency to target host and port in milliseconds (-1.0 if unreachable)");

    m.def("elevate_process_priority",
          [](int pid, int desired_nice) {
              int eff_nice = 0;
              std::string err;
              bool ok = stream_native::elevate_process_priority(pid, desired_nice, eff_nice, err);
              return py::make_tuple(ok, eff_nice, err);
          },
          py::arg("pid"), py::arg("desired_nice") = -10,
          "Elevates process priority (returns (success: bool, effective_nice: int, error_msg: str))");

    m.def("get_process_stats", &stream_native::get_process_stats,
          py::arg("pid"),
          "Directly reads /proc/[pid] to retrieve process CPU, memory, and thread metrics");
}
