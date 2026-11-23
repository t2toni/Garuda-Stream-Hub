#pragma once

#include <string>
#include <vector>
#include <chrono>
#include <deque>
#include <mutex>
#include <cstdint>

namespace stream_native {

struct ProcessStats {
    int pid;
    std::string name;
    std::string state;
    uint64_t vm_rss_kb;
    uint64_t cpu_user_time;
    uint64_t cpu_sys_time;
    int nice_level;
    int num_threads;
    bool is_running;
};

class JitterCalculator {
public:
    explicit JitterCalculator(size_t window_size = 30);
    void add_sample(double rtt_ms);
    double get_jitter_ms() const;
    double get_avg_rtt_ms() const;
    double get_min_rtt_ms() const;
    double get_max_rtt_ms() const;
    int get_recommended_buffer_ms() const;
    void reset();

private:
    size_t window_size_;
    mutable std::mutex mutex_;
    std::deque<double> rtt_samples_;
    double jitter_estimate_;
    double last_rtt_;
};

// Fast non-blocking socket ping measurement
double ping_host(const std::string& host, int port = 5555, int timeout_ms = 800);

// Elevate process nice level using native setpriority
bool elevate_process_priority(int pid, int desired_nice, int& effective_nice, std::string& error_msg);

// Direct /proc parser for process monitoring
ProcessStats get_process_stats(int pid);

} // namespace stream_native
