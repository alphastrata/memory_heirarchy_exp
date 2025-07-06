use rand::SeedableRng as _;
use rand::TryRngCore;
use rand::rngs::SmallRng;
use serde::{Deserialize, Serialize};

use std::ptr;
use std::time::Instant;

// Fixed seed for reproducible randomness
const SEED: u64 = 0x1234567890ABCDEF;

// Minimum and maximum buffer sizes for testing
const MIN_SIZE: usize = 512; // 512B
const MAX_SIZE: usize = 256 * 1024 * 1024; // 256MB

// Number of iterations for timing stability
const TIMING_ITERATIONS: usize = 1_000;
const WARMUP_ITERATIONS: usize = 50;

#[derive(Debug, Serialize, Deserialize)]
pub struct MemoryHierarchyResults {
    pub test_method: String,
    pub measurements: Vec<MemoryMeasurement>,
    pub detected_l1_size_kb: Option<u32>,
    pub detected_l2_size_kb: Option<u32>,
    pub detected_l3_size_kb: Option<u32>,
    pub l1_latency_ns: Option<f64>,
    pub l2_latency_ns: Option<f64>,
    pub l3_latency_ns: Option<f64>,
    pub dram_latency_ns: Option<f64>,
    pub cache_line_size: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryMeasurement {
    pub working_set_size_kb: u32,
    pub avg_latency_ns: f64,
    pub min_latency_ns: f64,
    pub max_latency_ns: f64,
    pub std_dev_ns: f64,
    pub iterations: usize,
}

// Pointer chasing node structure
#[repr(C)]
pub struct ChaseNode {
    pub next: *mut ChaseNode,
    pub data: u64, // Padding to ensure cache line usage
}

pub struct MemoryTester {
    rng: SmallRng,
}

impl Default for MemoryTester {
    fn default() -> Self {
        Self::new()
    }
}

impl MemoryTester {
    pub fn new() -> Self {
        let mut seed = [0u8; 32];
        let seed_bytes = SEED.to_le_bytes();
        seed[..8].copy_from_slice(&seed_bytes);

        Self {
            rng: SmallRng::from_seed(seed),
        }
    }

    /// Generate test sizes in powers of 2, with some intermediate values
    pub fn generate_test_sizes(&self) -> Vec<usize> {
        std::iter::successors(Some(MIN_SIZE), |&size| {
            if size <= MAX_SIZE / 2 {
                Some(size * 2)
            } else {
                None
            }
        })
        .flat_map(|size| {
            if size < MAX_SIZE / 2 {
                vec![size, size + size / 2]
            } else {
                vec![size]
            }
        })
        .filter(|&size| size <= MAX_SIZE)
        .collect()
    }

    /// Measure serial memory access latency
    pub fn measure_serial_access(&mut self, buffer_size: usize) -> MemoryMeasurement {
        let buffer = vec![0u8; buffer_size];

        // Warmup
        (0..WARMUP_ITERATIONS).for_each(|_| {
            self.serial_access_inner(&buffer);
        });

        // Actual measurements
        let latencies: Vec<f64> = (0..TIMING_ITERATIONS)
            .map(|_| {
                let start = Instant::now();
                let _result = self.serial_access_inner(&buffer);
                start.elapsed().as_nanos() as f64
            })
            .collect();

        self.calculate_statistics(buffer_size, latencies)
    }

    /// Measure pointer chasing latency
    pub fn measure_pointer_chase(&mut self, buffer_size: usize) -> MemoryMeasurement {
        let node_count = buffer_size / std::mem::size_of::<ChaseNode>();
        let nodes = self.create_chase_chain(node_count);

        // Warmup
        (0..WARMUP_ITERATIONS).for_each(|_| {
            self.pointer_chase_inner(&nodes);
        });

        // Actual measurements
        let latencies: Vec<f64> = (0..TIMING_ITERATIONS)
            .map(|_| {
                let start = Instant::now();
                let _result = self.pointer_chase_inner(&nodes);
                start.elapsed().as_nanos() as f64
            })
            .collect();

        self.calculate_statistics(buffer_size, latencies)
    }

    /// Serial memory access implementation
    fn serial_access_inner(&self, buffer: &[u8]) -> u64 {
        let stride = 64; // Cache line size

        (0..buffer.len())
            .step_by(stride)
            .map(|i| unsafe {
                // Use volatile read to prevent optimization
                ptr::read_volatile(&buffer[i] as *const u8) as u64
            })
            .fold(0u64, |acc, val| acc.wrapping_add(val))
    }

    /// Create a randomised pointer chase chain
    fn create_chase_chain(&mut self, node_count: usize) -> Vec<ChaseNode> {
        if node_count == 0 {
            return vec![];
        }

        let mut nodes: Vec<ChaseNode> = (0..node_count)
            .map(|i| ChaseNode {
                next: ptr::null_mut(),
                data: i as u64,
            })
            .collect();

        let mut indices: Vec<usize> = (0..node_count).collect();

        // Shuffle indices to create random access pattern
        (1..node_count).rev().for_each(|i| {
            let j = (self.rng.try_next_u64().unwrap() as usize) % (i + 1);
            indices.swap(i, j);
        });

        // Link nodes in shuffled order
        indices.iter().enumerate().for_each(|(i, &idx)| {
            let next_idx = indices[(i + 1) % node_count];
            let base_ptr = nodes.as_mut_ptr();
            unsafe {
                // Don't be afraid! raw pointer arithmetic to avoid double borrow
                (*base_ptr.add(idx)).next = base_ptr.add(next_idx);
            }
        });

        nodes
    }

    /// Pointer chasing implementation
    fn pointer_chase_inner(&self, nodes: &[ChaseNode]) -> u64 {
        if nodes.is_empty() {
            return 0;
        }

        let mut current = &nodes[0] as *const ChaseNode;
        let iterations = nodes.len() * 2; // Multiple passes through the chain

        (0..iterations)
            .map(|_| unsafe {
                let data = (*current).data;
                current = (*current).next as *const ChaseNode;
                if current.is_null() {
                    current = &nodes[0] as *const ChaseNode;
                }
                data
            })
            .fold(0u64, |acc, val| acc.wrapping_add(val))
    }

    /// Calculate statistics from timing measurements
    fn calculate_statistics(&self, buffer_size: usize, latencies: Vec<f64>) -> MemoryMeasurement {
        let count = latencies.len() as f64;
        let sum: f64 = latencies.iter().sum();
        let avg = sum / count;

        let min = latencies.iter().fold(f64::INFINITY, |a, &b| a.min(b));
        let max = latencies.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));

        let variance = latencies.iter().map(|&x| (x - avg).powi(2)).sum::<f64>() / count;
        let std_dev = variance.sqrt();

        MemoryMeasurement {
            working_set_size_kb: (buffer_size / 1024) as u32,
            avg_latency_ns: avg,
            min_latency_ns: min,
            max_latency_ns: max,
            std_dev_ns: std_dev,
            iterations: latencies.len(),
        }
    }

    /// Analyze measurements to detect cache hierarchy
    pub fn analyze_hierarchy(&self, measurements: &[MemoryMeasurement]) -> MemoryHierarchyResults {
        let mut results = MemoryHierarchyResults {
            test_method: String::new(),
            measurements: measurements.to_vec(),
            detected_l1_size_kb: None,
            detected_l2_size_kb: None,
            detected_l3_size_kb: None,
            l1_latency_ns: None,
            l2_latency_ns: None,
            l3_latency_ns: None,
            dram_latency_ns: None,
            cache_line_size: 64, // Common default
        };

        // Simple cliff detection
        let (_, _l1_detected, _l2_detected) = measurements.iter().enumerate().skip(1).fold(
            (0.0, false, false),
            |(prev_latency, l1_detected, l2_detected), (i, measurement)| {
                let latency_ratio = measurement.avg_latency_ns / prev_latency;

                //TODO match is easier to read
                // Detect significant latency increases (cliffs)
                if latency_ratio > 1.5 && !l1_detected {
                    results.detected_l1_size_kb = Some(measurements[i - 1].working_set_size_kb);
                    results.l1_latency_ns = Some(prev_latency);
                    (measurement.avg_latency_ns, true, l2_detected)
                } else if latency_ratio > 1.3 && l1_detected && !l2_detected {
                    results.detected_l2_size_kb = Some(measurements[i - 1].working_set_size_kb);
                    results.l2_latency_ns = Some(prev_latency);
                    (measurement.avg_latency_ns, l1_detected, true)
                } else if latency_ratio > 1.2 && l1_detected && l2_detected {
                    results.detected_l3_size_kb = Some(measurements[i - 1].working_set_size_kb);
                    results.l3_latency_ns = Some(prev_latency);
                    (measurement.avg_latency_ns, l1_detected, l2_detected)
                } else {
                    (measurement.avg_latency_ns, l1_detected, l2_detected)
                }
            },
        );

        // Set first measurement as baseline for fold
        if let Some(first_measurement) = measurements.first() {
            let _ = (first_measurement.avg_latency_ns, false, false);
        }

        // DRAM latency is typically the last measurement
        if let Some(last_measurement) = measurements.last() {
            results.dram_latency_ns = Some(last_measurement.avg_latency_ns);
        }

        results
    }

    pub fn run_test_suite(&mut self, method: &str) -> MemoryHierarchyResults {
        let sizes = self.generate_test_sizes();

        println!("Running {method} memory hierarchy test...");
        println!("Testing {} different working set sizes", sizes.len());

        let measurements: Vec<MemoryMeasurement> = sizes
            .iter()
            .enumerate()
            .map(|(i, &size)| {
                print!(
                    "Testing size: {} KB ({}/{})...",
                    size / 1024,
                    i + 1,
                    sizes.len()
                );

                let measurement = match method {
                    "serial" => self.measure_serial_access(size),
                    "pointer_chase" => self.measure_pointer_chase(size),
                    _ => panic!("Unknown test method: {method}"),
                };

                println!(" {:.2} ns avg", measurement.avg_latency_ns);
                measurement
            })
            .collect();

        let mut results = self.analyze_hierarchy(&measurements);
        results.test_method = method.to_string();

        results
    }
}
