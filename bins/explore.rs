use memory_hierarchy_explorer::MemoryTester;
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    let output_json = args.get(1).map(|s| s == "--json").unwrap_or(false);

    let mut tester = MemoryTester::new();
    let results = tester.run_test_suite("serial");

    if output_json {
        let json = serde_json::to_string_pretty(&results).unwrap();
        println!("{}", json);
    } else {
        print_human_readable(&results);
    }
}

fn print_human_readable(results: &memory_hierarchy_explorer::MemoryHierarchyResults) {
    println!("\n=== Serial Memory Access Analysis ===");

    if let Some(l1_size) = results.detected_l1_size_kb {
        println!(
            "L1 Cache: {} KB (latency: {:.2} ns)",
            l1_size,
            results.l1_latency_ns.unwrap_or(0.0)
        );
    }

    if let Some(l2_size) = results.detected_l2_size_kb {
        println!(
            "L2 Cache: {} KB (latency: {:.2} ns)",
            l2_size,
            results.l2_latency_ns.unwrap_or(0.0)
        );
    }

    if let Some(l3_size) = results.detected_l3_size_kb {
        println!(
            "L3 Cache: {} KB (latency: {:.2} ns)",
            l3_size,
            results.l3_latency_ns.unwrap_or(0.0)
        );
    }

    if let Some(dram_latency) = results.dram_latency_ns {
        println!("DRAM latency: {:.2} ns", dram_latency);
    }

    println!("\nDetailed measurements:");
    println!("Size (KB)\tAvg Latency (ns)\tMin (ns)\tMax (ns)\tStd Dev (ns)");
    println!("--------\t---------------\t--------\t--------\t------------");

    for measurement in &results.measurements {
        println!(
            "{}\t\t{:.2}\t\t{:.2}\t\t{:.2}\t\t{:.2}",
            measurement.working_set_size_kb,
            measurement.avg_latency_ns,
            measurement.min_latency_ns,
            measurement.max_latency_ns,
            measurement.std_dev_ns
        );
    }
}
