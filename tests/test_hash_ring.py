import sys
import os

# import from app.core
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.hash_ring import ConsistentHashRing

def test_consistent_hash_ring():
    print("Initializing Consistent Hash Ring...")
    ring = ConsistentHashRing(virtual_nodes=50)

    print("\nTest 1: Adding Nodes")
    nodes = ["http://server-1:8000", "http://server-2:8000", "http://server-3:8000"]
    for node in nodes:
        ring.add_node(node)
    print(f"Added {len(nodes)} nodes. Total vnodes on ring: {len(ring.hash_ring)}")
    assert len(ring.hash_ring) == 3 * 50, "Virtual node count mismatch!"
    print("Add nodes test passed.")

    print("\nTest 2: Key Consistency (Idempotency)")
    test_keys = ["192.168.1.10", "10.0.0.5", "172.16.0.25", "client-abc-xyz"]
    
    mapping_first_run = {}
    for key in test_keys:
        assigned_node = ring.get_node(key)
        mapping_first_run[key] = assigned_node
        print(f"Key '{key}' -> Assigned to {assigned_node}")

    for key in test_keys:
        assert ring.get_node(key) == mapping_first_run[key], f"Consistency failed for key {key}"
    print("Key consistency test passed.")

    print("\nTest 3: Distribution Balance Check")
    distribution = {node: 0 for node in nodes}
    total_samples = 1000
    mapping_client_nodes = {}
    for i in range(total_samples):
        assigned = ring.get_node(f"client-ip-{i}")
        distribution[assigned] += 1
        mapping_client_nodes[f"client-ip-{i}"] = assigned
    
    for node, count in distribution.items():
        percentage = (count / total_samples) * 100
        print(f"Node {node}: {count} requests ({percentage:.2f}%)")
    print("Distribution check complete.")

    print("\nTest 4: Node Removal & Failover")
    node_to_remove = "http://server-2:8000"
    print(f"Removing node: {node_to_remove}")
    ring.remove_node(node_to_remove)

    failover_routed_count = 0
    for i in range(total_samples):
        key = f"client-ip-{i}"
        old_node = mapping_client_nodes[key]
        new_node = ring.get_node(key)
        
        assert new_node != node_to_remove, f"Dead node {node_to_remove} still receiving traffic!"
        
        if old_node == node_to_remove:
            failover_routed_count += 1

    print(f"Successfully re-routed {failover_routed_count} keys from removed node to healthy neighbors.")
    print("Node removal and failover test passed!")

if __name__ == "__main__":
    test_consistent_hash_ring()