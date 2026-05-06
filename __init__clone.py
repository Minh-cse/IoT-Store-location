import logging
from azure.functions import EventHubEvent
from typing import List
import json
import os
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import CloudToDeviceMethod

truck_location = {}

def main(events: List[EventHubEvent]):
    for event in events:
        body = json.loads(event.get_body().decode('utf-8'))
        device_id = event.iothub_metadata['connection-device-id']

        lat = body['gps']['lat']
        lon = body['gps']['lon']

        new_status = 'arrived' if 'warehouse' in body else 'in_transit'
        previous_status = truck_location.get(device_id, {}).get('status', None)

        # Cập nhật vị trí
        truck_location[device_id] = {
            "lat": lat,
            "lon": lon,
            "status": new_status
        }

        # Chỉ gửi khi trạng thái thay đổi
        if new_status == previous_status:
            logging.info(f'Truck {device_id} vẫn {new_status}, bỏ qua')
            continue

        direct_method = CloudToDeviceMethod(method_name=new_status, payload='{}')
        logging.info(f'Sending direct method request for {direct_method.method_name} for device {device_id}')

        registry_manager_connection_string = os.environ['REGISTRY_MANAGER_CONNECTION_STRING']
        registry_manager = IoTHubRegistryManager(registry_manager_connection_string)

        try:
            registry_manager.invoke_device_method(device_id, direct_method)
            logging.info('Direct method request sent!')
        except Exception as e:
            logging.warning(f'Could not send direct method to {device_id}: {e}')
            logging.warning('Device may be offline')
