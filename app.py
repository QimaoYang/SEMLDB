# app.py

from flask import Flask, request, jsonify, abort
from flask_restx import Api, Resource
from flask_cors import CORS
from db_helper import DBHelper
from models import MODEL_CONFIG
import base64
import io
import threading
import numpy as np
import logging


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
# CORS added
CORS(app)

api: Api = Api(
    title='FET_DB API',
    version='1.0',
    description='v1.0',
    prefix='/v1'
)

# Initialize DBHelper
db_helper = DBHelper()

# Initialize Simulation Config if needed
# from simulation import SimulationConfig  # If SimulationConfig is used within simulation functions


@app.route('/simulation_data', methods=['GET'])
def check_simulation_data():
    device_type = request.args.get('device')
    sim_type = request.args.get('sim_type')

    if not device_type or not sim_type:
        return jsonify({"status": "error", "message": "Missing 'device' or 'sim_type' parameters."}), 400

    # Extract device parameters from the request
    parameters = {}
    for key, value in request.args.items():
        # Skip the device and sim_type parameters
        if key not in ['device', 'sim_type']:
            try:
                parameters[key] = float(value)
            except ValueError:
                return jsonify({
                    "status": "error",
                    "message": f"Parameter '{key}' should be a number."
                }), 400
            
    device = MODEL_CONFIG.get(device_type)

    # Fetch simulation data from DB
    logger.info(f"Fetching data for device '{device}' with parameters: {parameters}")
    
    complete_data, exact_match, distance, matched_params = device['postprocess'](db_helper, sim_type, parameters)

    if complete_data:
        # Construct response with the complete data already in the right format
        response_data = {
            "status": "success",
            "data": complete_data,
            "exact_match": exact_match,
        }
        
        if not exact_match:
            response_data.update({
                "distance": distance,
                "matched_parameters": matched_params,
                "message": "Nearest match found"
            })
        else:
            response_data["message"] = "Exact match found"
            
        return jsonify(response_data)
    else:
        return jsonify({
            "status": "error",
            "message": f"No {sim_type} data found for '{device}' with the given or similar parameters."
        }), 404


@app.route('/run_simulation', methods=['POST'])
def RunSimulation():
    """
    Endpoint: POST /run_simulation
    JSON Body Parameters:
        - device_type: Type of the device (e.g., 'CNTFET')
        - sim_type: Type of simulation to run ('Synopsys')
        - Other device-specific parameters
    """
    if not request.is_json:
        return jsonify({"message": "Request body must be JSON."}), 400

    data = request.get_json()
    print(data)
    device_type = data.get('device_type')
    sim_type = data.get('sim_type')

    if not device_type or not sim_type:
        return jsonify({"message": "Missing 'device_type' or 'sim_type' in request body."}), 400

    # Extract device-specific parameters
    parameters = data.get('parameters', {})
    if not parameters:
        return jsonify({"message": "Missing 'parameters' in request body."}), 400

    # Retrieve the simulation function from model_config
    try:
        device = MODEL_CONFIG.get(device_type)
        if sim_type.lower() not in list(device['simulation_func'].keys()):
            return jsonify({"message": f"Unsupported simulation type '{sim_type}'."}), 400
        
        simulation_func = device['simulation_func'][sim_type.lower()]

        if not simulation_func:
            return jsonify({"message": f"No simulation function defined for device type '{device_type}'."}), 400

        simulation_data = simulation_func(parameters)

        if simulation_data is None:
            return jsonify({"message": "Simulation failed."}), 500
       
        response_data = {
            "status": "success",
            "data": simulation_data,
        }

        return jsonify(response_data)

    except Exception as e:
            print(f"Simulation failed: {str(e)}")
            return jsonify({
                "status": "error",
                "message": f"Simulation failed: {str(e)}"
            }), 500


# Add resources to API
# api.add_resource(CheckSimulationData, '/simulation_data')
# api.add_resource(RunSimulation, '/run_simulation')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=20501, debug=True)
