use std::time::{Instant, Duration};
use rand::prelude::*;
use std::fs::File;
use std::io::Write;


// Using my machine's AMD 5950x' values, you should put yours here to help get a good 'tune'
const L1_SIZE: usize = 64 * 1024; // 64 KB
const L2_SIZE: usize = 512 * 1024; // 512 KB
const L3_SIZE: usize = 64 * 1024 * 1024; // 64 MB
const WARMUP_RUNS: usize = 3;
const MEASUREMENT_RUNS: usize = 5;
const ACCESSES_PER_RUN: usize = 10_000_000;
const CACHE_LINE_SIZE: usize = 64;

fn main() {
    println!("Running cache measurements...");
    std::fs::create_dir_all("results").unwrap();
    
    let pc_results = measure_access_pattern(true);
    let seq_results = measure_access_pattern(false);
    save_combined_data("results/cache_data.csv", &pc_results, &seq_results);
    println!("\nData saved to results/cache_data.csv");
}

fn measure_access_pattern(pointer_chasing: bool) -> Vec<(String, f64, usize)> {
    let mut rng = rand::thread_rng();
    let mut results = Vec::new();
    let test_sizes = [
        ("L1", L1_SIZE / 2),
        ("L1-L2", L1_SIZE * 3/2),
        ("L2", L2_SIZE / 2),
        ("L2-L3", L2_SIZE * 3/2),
        ("L3", L3_SIZE / 2),
        ("RAM", L3_SIZE * 2),
    ];

    for (label, size) in test_sizes {
        println!("Testing {} ({} bytes) with {}...",
            label, size,
            if pointer_chasing { "pointer chasing" } else { "sequential" }
        );

        let mut buffer = vec![0u8; size];
        let pattern = if pointer_chasing {
            create_pointer_chasing_pattern(size, &mut rng)
        } else {
            create_sequential_pattern(size)
        };

        // Warm up
        for i in 0..size {
            buffer[i] = (i % 256) as u8;
        }
        std::hint::black_box(&buffer);

        for _ in 0..WARMUP_RUNS {
            run_benchmark(&buffer, &pattern, pointer_chasing);
        }

        let mut total = Duration::ZERO;
        for _ in 0..MEASUREMENT_RUNS {
            let start = Instant::now();
            run_benchmark(&buffer, &pattern, pointer_chasing);
            total += start.elapsed();
        }

        let avg_ns = total.as_nanos() as f64 / (MEASUREMENT_RUNS * ACCESSES_PER_RUN) as f64;
        let allocated_bytes = buffer.capacity();
        results.push((label.to_string(), avg_ns, allocated_bytes));
        println!("  Avg latency: {:.2} ns, Allocated: {} bytes", avg_ns, allocated_bytes);
    }
    results
}

fn run_benchmark(buffer: &[u8], pattern: &[usize], pointer_chasing: bool) {
    if pointer_chasing {
        let mut idx = 0;
        for _ in 0..ACCESSES_PER_RUN {
            idx = pattern[idx];
            let v = buffer[(idx * CACHE_LINE_SIZE) % buffer.len()];
            std::hint::black_box(v);
        }
    } else {
        for i in 0..ACCESSES_PER_RUN {
            let v = buffer[(i * CACHE_LINE_SIZE) % buffer.len()];
            std::hint::black_box(v);
        }
    }
}

fn create_pointer_chasing_pattern(size: usize, rng: &mut ThreadRng) -> Vec<usize> {
    let n = size / CACHE_LINE_SIZE;
    let mut chain = vec![0; n];
    let mut indices: Vec<_> = (0..n).collect();
    indices.shuffle(rng);
    for i in 0..n {
        chain[indices[i]] = indices[(i + 1) % n];
    }
    chain
}

fn create_sequential_pattern(size: usize) -> Vec<usize> {
    (0..size / CACHE_LINE_SIZE).collect()
}

fn save_combined_data(path: &str, pc: &[(String, f64, usize)], seq: &[(String, f64, usize)]) {
    let mut file = File::create(path).unwrap();
    writeln!(file, "cache_level,pointer_chasing_ns,serial_ns,allocated_bytes").unwrap();
    for ((pc_lvl, pc, pc_bytes), (seq_lvl, seq, seq_bytes)) in pc.iter().zip(seq.iter()) {
        assert_eq!(pc_lvl, seq_lvl);
        assert_eq!(pc_bytes, seq_bytes);
        writeln!(file, "{},{},{},{}", pc_lvl, pc, seq, pc_bytes).unwrap();
    }
}