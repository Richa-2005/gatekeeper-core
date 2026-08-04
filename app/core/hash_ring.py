import hashlib
import bisect

class ConsistentHashRing:
    def __init__(self, virtual_nodes: int = 100):
        self.virtual_nodes = virtual_nodes
        self.hash_ring = {}
        self.sorted_hashes = []

    def hash_node(self, key):
        return int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)

    def add_node(self,node_url):
        for node in range(self.virtual_nodes):
            hashed_key = self.hash_node(f"{node_url}-{node}")
            self.hash_ring[hashed_key] = node_url

        self.sorted_hashes = sorted(self.hash_ring.keys())

    def remove_node(self,node_url):
        for node in range(self.virtual_nodes):
            hashed_key = self.hash_node(f"{node_url}-{node}")
            if hashed_key in self.hash_ring:
                del self.hash_ring[hashed_key]
        self.sorted_hashes = sorted(self.hash_ring.keys())

    def get_node(self, key):
        if not self.hash_ring:
            return None
        hashed_key = self.hash_node(key)
       
        idx = bisect.bisect_left(self.sorted_hashes, hashed_key)
        
        if idx == len(self.sorted_hashes):
            idx = 0
            
        return self.hash_ring[self.sorted_hashes[idx]]