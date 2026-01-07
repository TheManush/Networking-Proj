"""
Flow Control Handler
Implements congestion control and flow control mechanisms
"""

import time
import threading
from collections import deque


class FlowController:
    """
    Implements flow control and congestion control for VPN tunnel
    Uses sliding window and congestion avoidance algorithms
    """
    
    def __init__(self, initial_window_size: int = 65536):
        # Sliding window parameters
        self.window_size = initial_window_size  # bytes
        self.max_window_size = 1048576  # 1 MB
        self.min_window_size = 4096     # 4 KB
        
        # Congestion control state
        self.ssthresh = initial_window_size // 2  # Slow start threshold
        self.cwnd = self.min_window_size          # Congestion window
        self.in_slow_start = True
        
        # RTT (Round Trip Time) measurement
        self.rtt_samples = deque(maxlen=10)
        self.smoothed_rtt = 0.0
        self.rtt_variance = 0.0
        
        # Packet tracking
        self.packets_in_flight = 0
        self.total_packets_sent = 0
        self.total_packets_acked = 0
        self.retransmissions = 0
        
        # Statistics
        self.throughput_samples = deque(maxlen=20)
        self.last_stat_time = time.time()
        self.bytes_transferred = 0
        
        self.lock = threading.Lock()
    
    def can_send(self, data_size: int) -> bool:
        """
        Check if we can send data based on flow control window
        
        Args:
            data_size: Size of data to send
            
        Returns:
            bool: True if we can send
        """
        with self.lock:
            # Check if within congestion window
            bytes_in_flight = self.packets_in_flight * 1024  # Approximate
            return (bytes_in_flight + data_size) <= self.cwnd
    
    def on_packet_sent(self, packet_size: int):
        """Called when a packet is sent"""
        with self.lock:
            self.packets_in_flight += 1
            self.total_packets_sent += 1
            self.bytes_transferred += packet_size
    
    def on_ack_received(self, packet_size: int, rtt: float):
        """
        Called when acknowledgment is received
        Updates congestion window based on TCP-like algorithm
        
        Args:
            packet_size: Size of acknowledged packet
            rtt: Round trip time in seconds
        """
        with self.lock:
            self.packets_in_flight -= 1
            self.total_packets_acked += 1
            
            # Update RTT estimates
            self._update_rtt(rtt)
            
            # Update congestion window (TCP Reno-like)
            if self.in_slow_start:
                # Slow start: exponential growth
                self.cwnd += packet_size
                
                # Check if we should exit slow start
                if self.cwnd >= self.ssthresh:
                    self.in_slow_start = False
            else:
                # Congestion avoidance: linear growth
                increment = (packet_size * packet_size) // self.cwnd
                self.cwnd += max(1, increment)
            
            # Cap at max window size
            self.cwnd = min(self.cwnd, self.max_window_size)
            
            # Update throughput statistics
            self._update_throughput()
    
    def on_packet_loss(self):
        """
        Called when packet loss is detected
        Implements congestion control response
        """
        with self.lock:
            self.retransmissions += 1
            
            # Multiplicative decrease
            self.ssthresh = max(self.cwnd // 2, self.min_window_size)
            self.cwnd = self.ssthresh
            self.in_slow_start = False
    
    def on_timeout(self):
        """Called when timeout occurs"""
        with self.lock:
            # Severe congestion indication
            self.ssthresh = max(self.cwnd // 2, self.min_window_size)
            self.cwnd = self.min_window_size
            self.in_slow_start = True
    
    def _update_rtt(self, rtt_sample: float):
        """Update RTT estimates using exponential moving average"""
        self.rtt_samples.append(rtt_sample)
        
        if self.smoothed_rtt == 0:
            # First sample
            self.smoothed_rtt = rtt_sample
            self.rtt_variance = rtt_sample / 2
        else:
            # Exponential moving average
            alpha = 0.125  # Smoothing factor
            beta = 0.25
            
            error = rtt_sample - self.smoothed_rtt
            self.smoothed_rtt += alpha * error
            self.rtt_variance += beta * (abs(error) - self.rtt_variance)
    
    def _update_throughput(self):
        """Calculate current throughput"""
        current_time = time.time()
        time_delta = current_time - self.last_stat_time
        
        if time_delta >= 1.0:  # Update every second
            throughput = self.bytes_transferred / time_delta  # bytes/sec
            self.throughput_samples.append(throughput)
            
            self.bytes_transferred = 0
            self.last_stat_time = current_time
    
    def get_timeout(self) -> float:
        """
        Calculate retransmission timeout based on RTT
        
        Returns:
            float: Timeout in seconds
        """
        with self.lock:
            if self.smoothed_rtt == 0:
                return 1.0  # Default 1 second
            
            # RTO = SRTT + 4 * RTTVAR (as per RFC 6298)
            rto = self.smoothed_rtt + 4 * self.rtt_variance
            return max(0.2, min(rto, 60.0))  # Clamp between 200ms and 60s
    
    def get_stats(self) -> dict:
        """Get flow control statistics"""
        with self.lock:
            avg_throughput = 0
            if self.throughput_samples:
                avg_throughput = sum(self.throughput_samples) / len(self.throughput_samples)
            
            avg_rtt = 0
            if self.rtt_samples:
                avg_rtt = sum(self.rtt_samples) / len(self.rtt_samples)
            
            return {
                'congestion_window': self.cwnd,
                'ssthresh': self.ssthresh,
                'in_slow_start': self.in_slow_start,
                'packets_in_flight': self.packets_in_flight,
                'total_sent': self.total_packets_sent,
                'total_acked': self.total_packets_acked,
                'retransmissions': self.retransmissions,
                'avg_rtt_ms': avg_rtt * 1000,
                'smoothed_rtt_ms': self.smoothed_rtt * 1000,
                'avg_throughput_mbps': (avg_throughput * 8) / (1024 * 1024),
                'window_utilization': (self.packets_in_flight * 1024) / self.cwnd if self.cwnd > 0 else 0
            }
