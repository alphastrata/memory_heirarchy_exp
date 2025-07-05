// Filename: src/main.rs
use std::time::{Instant, Duration};
use rand::prelude::*;
use std::fs::File;
use std::io::Write;

// Target your specific cache sizes
const L1_SIZE: usize = 64 * 1024;      // 64KB
const L2_SIZE: usize = 512 * 1024;     // 512KB 
const L3_SIZE: usize = 64 * 1024 * 1024; // 64MB
const MAX_SIZE: usize = 128 * 1024 * 1024; // 128MB (to measure beyond L3)

// Test parameters
const WARMUP_RUNS: usize = 3;
const MEASUREMENT_RUNS: usize = 5;
const ACCESSES_PER_RUN: usize = 10_000_000;
const CACHE_LINE_SIZE: usize = 64;

fn main() {
    println!("Running cache hierarchy measurement for:");
    println!("- L1: 64KB");
    println!("- L2: 512KB");
    println!("- L3: 64MB");
    
    std::fs::create_dir_all("results").unwrap();
    
    let results = measure_cache_hierarchy();
    save_data("results/cache_latency.csv", &results);
    
    println!("\nMeasurement complete!");
    println!("Results saved to results/cache_latency.csv");
}

fn measure_cache_hierarchy() -> Vec<(String, f64)> {
    let mut rng = rand::thread_rng();
    let mut results = Vec::new();
    
    // Test sizes targeting each cache level
    let test_sizes = [
        ("L1", L1_SIZE / 2),      // Fit comfortably in L1
        ("L1-L2", L1_SIZE * 3/2), // Just beyond L1
        ("L2", L2_SIZE / 2),      // Fit in L2
        ("L2-L3", L2_SIZE * 3/2), // Just beyond L2
        ("L3", L3_SIZE / 2),      // Fit in L3
        ("RAM", L3_SIZE * 2),     // Beyond L3
    ];
    
    for (label, size) in test_sizes {
        println!("\nTesting {} ({} bytes)...", label, size);
        
        // Allocate memory and create pointer chasing pattern
        let mut buffer = vec![0u8; size];
        let chain = create_pointer_chasing_pattern(size, &mut rng);
        
        // Warm up the memory
        for i in 0..size {
            buffer[i] = (i % 256) as u8;
        }
        std::hint::black_box(&buffer);
        
        // Warm up runs (not measured)
        for _ in 0..WARMUP_RUNS {
            pointer_chasing_benchmark(&buffer, &chain);
        }
        
        // Actual measurement runs
        let mut total_duration = Duration::ZERO;
        for _ in 0..MEASUREMENT_RUNS {
            let start = Instant::now();
            pointer_chasing_benchmark(&buffer, &chain);
            total_duration += start.elapsed();
        }
        
        let avg_latency = total_duration.as_nanos() as f64 / 
                         (MEASUREMENT_RUNS * ACCESSES_PER_RUN) as f64;
        
        results.push((label.to_string(), avg_latency));
        println!("  Avg latency: {:.2} ns", avg_latency);
    }
    
    results
}

fn pointer_chasing_benchmark(buffer: &[u8], chain: &[usize]) {
    let mut current_idx = 0;
    for _ in 0..ACCESSES_PER_RUN {
        current_idx = chain[current_idx];
        let buffer_idx = current_idx * CACHE_LINE_SIZE;
        if buffer_idx < buffer.len() {
            let value = buffer[buffer_idx];
            std::hint::black_box(value);
        }
    }
}

fn create_pointer_chasing_pattern(
    size: usize,
    rng: &mut ThreadRng
) -> Vec<usize> {
    let num_elements = size / CACHE_LINE_SIZE;
    let mut chain = vec![0usize; num_elements];
    let mut indices: Vec<usize> = (0..num_elements).collect();
    indices.shuffle(rng);
    
    for i in 0..num_elements {
        chain[indices[i]] = indices[(i + 1) % num_elements];
    }
    
    chain
}

fn save_data(filename: &str, results: &[(String, f64)]) {
    let mut file = File::create(filename).unwrap();
    writeln!(file, "cache_level,latency_ns").unwrap();
    
    for (level, latency) in results {
        writeln!(file, "{},{}", level, latency).unwrap();
    }
}