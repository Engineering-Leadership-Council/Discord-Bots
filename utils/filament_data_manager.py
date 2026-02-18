import json
import os
import asyncio
from datetime import datetime

class FilamentDataManager:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.inventory_file = os.path.join(data_path, "inventory.json")
        self.logs_file = os.path.join(data_path, "logs.json")
        self.inventory = self.load_json(self.inventory_file)
        self.logs = self.load_json(self.logs_file)

    def load_json(self, filename):
        if not os.path.exists(filename):
            return []
        
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if not content.strip(): 
                    return []
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            print(f"JSON_LOAD_ERROR: {filename} - {e}")
            return []
        return []

    def save_json(self, filename, data):
        tmp_filename = f"{filename}.tmp"
        try:
            with open(tmp_filename, 'w') as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_filename, filename)
        except Exception as e:
            print(f"Error saving {filename}: {e}")

    def get_inventory(self):
        # Reload to ensure fresh data
        self.inventory = self.load_json(self.inventory_file)
        return self.inventory

    def get_logs(self):
         # Reload to ensure fresh data
        self.logs = self.load_json(self.logs_file)
        return self.logs

    def update_filament_weight(self, filament_id, amount_used):
        """Reduces the weight of a filament by amount_used."""
        self.inventory = self.load_json(self.inventory_file) # Ensure fresh data before update
        for item in self.inventory:
            if item['id'] == filament_id:
                item['weight_g'] = round(max(0, item['weight_g'] - amount_used), 2)
                self.save_json(self.inventory_file, self.inventory)
                return True
        return False

    def add_inventory_item(self, type_name, brand, color, weight):
        """Adds a new filament reel to inventory."""
        self.inventory = self.load_json(self.inventory_file) # Ensure fresh
        new_id = 1
        if self.inventory:
            new_id = max(item['id'] for item in self.inventory) + 1
        
        new_item = {
            "id": new_id,
            "type": type_name,
            "brand": brand,
            "color": color,
            "weight_g": round(weight, 2)
        }
        self.inventory.append(new_item)
        self.save_json(self.inventory_file, self.inventory)
        return new_id

    def log_usage(self, user_name, filament_id, amount_used):
        """Records a usage event."""
        # Find filament details for the log
        self.inventory = self.load_json(self.inventory_file)
        filament_details = next((item for item in self.inventory if item['id'] == filament_id), None)
        filament_str = f"{filament_details['color']} {filament_details['type']}" if filament_details else "Unknown"

        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user_name,
            "filament_id": filament_id,
            "filament_desc": filament_str,
            "amount_used": amount_used
        }
        
        self.logs = self.load_json(self.logs_file)
        self.logs.append(log_entry)
        self.save_json(self.logs_file, self.logs)
