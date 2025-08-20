from pymongo import MongoClient
from gridfs import GridFS
import numpy as np


class DBHelper:
    def __init__(self, mongo_host='0.0.0.0', mongo_port=20502, db_name='transistors'):
        """Initializes the connection to MongoDB."""
        username = 'FETDB'
        password = 'FET0B123!'
        auth_source = 'transistors'

        # Connection string
        self.client = MongoClient(
            host=mongo_host,
            port=mongo_port,
            username=username,
            password=password,
            authSource=auth_source,
            authMechanism='SCRAM-SHA-256'
        )
        self.db = self.client[db_name]
        self.fs = GridFS(self.db)  # Note: You might not need GridFS anymore
        self.collection = self.db['devices']

    def get_device_by_type(self, device_type):
        """Fetch all devices of a certain type."""
        query = {"device": device_type}
        return list(self.collection.find(query))
    
    def get_devices_by_parameters(self, device_type, parameters):
        """
        Fetch all devices that match a certain set of parameters.
        parameters: Dictionary of parameters to filter by, e.g.,
                     {"tox": 2.5, "Lch": 1.2}
        """
        query = {'device': device_type}
        for key, value in parameters.items():
            query[f'device_params.{key}'] = value
        return self.collection.find_one(query)

    def get_simulation_data(self, device_type, parameters, simulation_type):
        """
        Retrieves device simulation data based on device, device_params, and simulation type.
        First tries exact match, then finds nearest if no exact match exists.
        
        Args:
            device_type (str): Type of the device
            parameters (dict): Device parameters to match
            simulation_type (str): Type of simulation data to retrieve
        
        Returns:
            tuple: (complete_device_data, exact_match, distance, matched_params)
                where complete_device_data contains the full device document with
                simulation_data restructured to be at the top level
        """
        # First try exact match
        device = self.get_devices_by_parameters(device_type, parameters)
        
        if device:
            simulation_data = device.get('simulation_data', {}).get(simulation_type, {})
            if simulation_data:
                # Create a complete data item
                complete_data = {
                    "device": device.get('device'),
                    "simulation_type": simulation_type,
                    "device_params": device.get('device_params', {}),
                    "simulation_data": simulation_data
                }
                return complete_data, True, None, parameters
        
        # If no exact match, get all parameter combinations and find nearest
        available_params = self.get_all_parameter_combinations(device_type)
        
        if not available_params:
            return None, False, None, None
            
        nearest_id, nearest_params, distance = self.find_nearest_parameters(parameters, available_params)
        
        if nearest_id:
            device = self.collection.find_one({"_id": nearest_id})
            if device:
                simulation_data = device.get('simulation_data', {}).get(simulation_type, {})
                if simulation_data:
                    # Create a complete data item for the nearest match
                    complete_data = {
                        "device": device.get('device'),
                        "simulation_type": simulation_type,
                        "device_params": device.get('device_params', {}),
                        "simulation_data": simulation_data
                    }
                    return complete_data, False, distance, nearest_params
        
        return None, False, None, None

    def insert_device(self, device_data):
        """Inserts a new device document into the collection."""
        return self.collection.insert_one(device_data).inserted_id

    def update_device_simulation_data(self, device_id, sim_type, sim_data):
        """
        Update the simulation data for a given device by its _id.
        """
        query = {"_id": device_id}
        update = {"$set": {f"simulation_data.{sim_type}": sim_data}}
        return self.collection.update_one(query, update).modified_count

    def delete_device(self, device_id):
        """Deletes a device document by its _id."""
        return self.collection.delete_one({"_id": device_id}).deleted_count

    def get_all_device_types(self):
        """Fetch all unique device types from the collection."""
        return self.collection.distinct("device")

    def get_all_devices(self):
        """Fetch all devices regardless of type."""
        return list(self.collection.find())

    def close(self):
        """Closes the MongoDB connection."""
        self.client.close()

    def find_nearest_parameters(self, target_params, available_params):
        """
        Find the nearest parameter set from available parameters using vector comparison.
        
        Args:
            target_params (dict): Target parameters to match
            available_params (list): List of dictionaries containing available parameter combinations
            
        Returns:
            tuple: (device_id, parameters, similarity_score)
        """
        param_keys = list(target_params.keys())
        target_vector = np.array([float(target_params[k]) for k in param_keys])
        
        best_match = None
        best_score = float('inf')
        best_id = None
        
        for param_set in available_params:
            # Skip if any parameter is missing
            if not all(k in param_set['device_params'] for k in param_keys):
                continue
                
            # Create vector from parameters
            current_vector = np.array([float(param_set['device_params'][k]) for k in param_keys])
            
            # Calculate difference
            diff_vector = target_vector - current_vector
            
            # Calculate weighted score based on parameter type
            score = 0
            for i, key in enumerate(param_keys):
                diff = diff_vector[i]
                
                # For parameters that can be zero (like sca_flag), use absolute difference
                if key == 'sca_flag' or target_vector[i] == 0:
                    score += diff**2
                else:
                    # For non-zero parameters, use relative difference
                    score += (diff / target_vector[i])**2
            
            score = np.sqrt(score)
            
            if score < best_score:
                best_score = score
                best_match = param_set['device_params']
                best_id = param_set['_id']
        
        return best_id, best_match, best_score
    
    def get_all_parameter_combinations(self, device_type):
        """
        Get all unique parameter combinations for a device type.
        Returns a list of parameter dictionaries and their corresponding device IDs.
        """
        pipeline = [
            {"$match": {"device": device_type}},
            {"$project": {
                "_id": 1,
                "device_params": 1
            }}
        ]
        
        return list(self.collection.aggregate(pipeline))
    
    def get_unique_parameter_values(self, device_type, parameter_name):
        """
        Get all unique values for a specific parameter of a device type.
        
        Args:
            device_type (str): Type of the device
            parameter_name (str): Name of the parameter
            
        Returns:
            list: List of unique parameter values
        """
        return self.collection.distinct(f"device_params.{parameter_name}", 
                                       {"device": device_type})


