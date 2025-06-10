import socket
import threading
import datetime
import pandas as pd
import folium
from folium.plugins import AntPath
import webbrowser
class SharedData:
    last_client_address = None

def decode_imei(hex_str):
    try:
        return bytes.fromhex(hex_str).decode("ascii")
    except Exception:
        return hex_str

shared_data = SharedData()

MAX_BYTES = 176
table_data = []
table_headers = []
coordenadas_mapa = []  # Lista para acumular todos los puntos

# Limpiar archivos de texto al iniciar el script
open("tramas_procesadas.txt", "w").close()
open("tag_parce.txt", "w").close()


def calculate_crc_modbus(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, byteorder='little')


def extract_tags(tags_data):
    """Extrae los tags de la trama según los diccionarios de tags de 1 y 2 bytes"""
    tags_dict_1byte = {
        		'01': {'name': 'HW', 'length': 1},
                '02': {'name': 'FW', 'length': 1},
                '03': {'name': 'IMEI', 'length': 15},
                '04': {'name': 'ID', 'length': 2},
                '10': {'name': 'Consecutivo', 'length': 2},
                '20': {'name': 'fecha', 'length': 4},
                '30': {'name': 'coordenadas', 'length': 9},
                '33': {'name': 'speed', 'length': 4},
                '34': {'name': 'Altura', 'length': 2},
                '35': {'name': 'HDOP', 'length': 1},
                '40': {'name': 'Status of device', 'length': 2},
                '41': {'name': 'Supply voltage, mV', 'length': 2},
                '42': {'name': 'Battery voltage, mV', 'length': 2},
                '43': {'name': 'Inside temperature, °C', 'length': 1},
                '44': {'name': 'Acceleration', 'length': 4},
                '45': {'name': 'Status of outputs', 'length': 2},
                '46': {'name': 'Status of inputs', 'length': 2},
                '50': {'name': 'Input voltage 0', 'length': 2},
                '51': {'name': 'Input voltage 1', 'length': 2},
                '52': {'name': 'Input voltage 2', 'length': 2},
                '53': {'name': 'Input voltage 3', 'length': 2},
                '58': {'name': 'RS232 0', 'length': 2},
                '59': {'name': 'RS232 1', 'length': 2},
                '70': {'name': 'Thermometer 0 identifier and value', 'length': 2},
                '71': {'name': 'Thermometer 1 identifier and value', 'length': 2},
                '72': {'name': 'Thermometer 2 identifier and value', 'length': 2},
                '73': {'name': 'Thermometer 3 identifier and value', 'length': 2},
                '74': {'name': 'Thermometer 4 identifier and value', 'length': 2},
                '75': {'name': 'Thermometer 5 identifier and value', 'length': 2},
                '76': {'name': 'Thermometer 6 identifier and value', 'length': 2},
                '77': {'name': 'Thermometer 7 identifier and value', 'length': 2},
                '90': {'name': 'First iButton key identification', 'length': 4},
                'C0': {'name': 'CAN_A0', 'length': 4},
                'C1': {'name': 'CAN_A1', 'length': 4},
                'C2': {'name': 'CAN_B0', 'length': 4},
                'C3': {'name': 'CAN_B1', 'length': 4},
                'C4': {'name': 'CAN8BITR0', 'length': 1},
                'C5': {'name': 'CAN8BITR1', 'length': 1},
                'C6': {'name': 'CAN8BITR2', 'length': 1},
                'C7': {'name': 'CAN8BITR3', 'length': 1},
                'C8': {'name': 'CAN8BITR4', 'length': 1},
                'C9': {'name': 'CAN8BITR5', 'length': 1},
                'CA': {'name': 'CAN8BITR6', 'length': 1},
                'CB': {'name': 'CAN8BITR7', 'length': 1},
                'CC': {'name': 'CAN8BITR8', 'length': 1},
                'CD': {'name': 'CAN8BITR9', 'length': 1},
                'CE': {'name': 'CAN8BITR10', 'length': 1},
                'CF': {'name': 'CAN8BITR11', 'length': 1},
                'D0': {'name': 'CAN8BITR12', 'length': 1},
                'D1': {'name': 'CAN8BITR13', 'length': 1},
                'D2': {'name': 'CAN8BITR14', 'length': 1},
                'D3': {'name': '2_iButton key', 'length': 4},
                'D4': {'name': 'Odometro GPS', 'length': 4},
                'D5': {'name': 'State of iButton keys', 'length': 1},
                'D6': {'name': 'CAN16BITR0', 'length': 2},
                'D7': {'name': 'CAN16BITR1', 'length': 2},
                'D8': {'name': 'CAN16BITR2', 'length': 2},
                'D9': {'name': 'CAN16BITR3', 'length': 2},
                'DA': {'name': 'CAN16BITR4', 'length': 2},
                'DB': {'name': 'CAN32BITR0', 'length': 4},
                'DC': {'name': 'CAN32BITR1', 'length': 4},
                'DD': {'name': 'CAN32BITR2', 'length': 4},
                'DE': {'name': 'CAN32BITR3', 'length': 4},
                'DF': {'name': 'CAN32BITR4', 'length': 4},
                '54': {'name': 'Input 4 values', 'length': 2},
                '55': {'name': 'Input 5 values', 'length': 2},
                '56': {'name': 'Input 6 values', 'length': 2},
                '57': {'name': 'Input 7 values', 'length': 2},
                '80': {'name': 'Zero DS1923 sensor', 'length': 3},
                '81': {'name': 'The 1st DS1923 sensor', 'length': 3},
                '82': {'name': 'The 2st DS1923 sensor', 'length': 3},
                '83': {'name': 'The 3st DS1923 sensor', 'length': 3},
                '84': {'name': 'The 4st DS1923 sensor', 'length': 3},
                '85': {'name': 'The 5st DS1923 sensor', 'length': 3},
                '86': {'name': 'The 6st DS1923 sensor', 'length': 3},
                '87': {'name': 'The 7st DS1923 sensor', 'length': 3},
                '60': {'name': 'RS485 [0]', 'length': 2},
                '61': {'name': 'RS485 [1]', 'length': 2},
                '62': {'name': 'RS485 [2]', 'length': 2},
                '63': {'name': 'RS485 [3]', 'length': 3},
                '64': {'name': 'RS485 [4]', 'length': 3},
                '65': {'name': 'RS485 [5]', 'length': 3},
                '66': {'name': 'RS485 [6]', 'length': 3},
                '67': {'name': 'RS485 [7]', 'length': 3},
                '68': {'name': 'RS485 [8]', 'length': 3},
                '69': {'name': 'RS485 [9]', 'length': 3},
                '6A': {'name': 'RS485 [10]', 'length': 3},
                '6B': {'name': 'RS485 [11]', 'length': 3},
                '6C': {'name': 'RS485 [12]', 'length': 3},
                '6D': {'name': 'RS485 [13]', 'length': 3},
                '6E': {'name': 'RS485 [14]', 'length': 3},
                '6F': {'name': 'RS485 [15]', 'length': 3},
                '88': {'name': 'Extended data RS232[0]', 'length': 1},
                '89': {'name': 'Extended data RS232[1]', 'length': 1},
                '8A': {'name': 'Temperature from fuel', 'length': 1},
                '8B': {'name': 'Temperature from fuel', 'length': 1},
                '8C': {'name': 'Temperature from fuel', 'length': 1},
                '78': {'name': 'Input 8 value', 'length': 2},
                '79': {'name': 'Input 9 value', 'length': 2},
                '7A': {'name': 'Input 10 value', 'length': 2},
                '7B': {'name': 'Input 11 value', 'length': 2},
                '7C': {'name': 'Input 12 value', 'length': 2},
                '7d': {'name': 'Input 13 value', 'length': 2},
                '21': {'name': 'Milliseconds', 'length': 2},
                'A0': {'name': 'CAN8BITR15', 'length': 1},
                'A1': {'name': 'CAN8BITR16', 'length': 1},
                'A2': {'name': 'CAN8BITR17', 'length': 1},
                'A3': {'name': 'CAN8BITR18', 'length': 1},
                'A4': {'name': 'CAN8BITR19', 'length': 1},
                'A5': {'name': 'CAN8BITR20', 'length': 1},
                'A6': {'name': 'CAN8BITR21', 'length': 1},
                'A7': {'name': 'CAN8BITR22', 'length': 1},
                'A8': {'name': 'CAN8BITR23', 'length': 1},
                'A9': {'name': 'CAN8BITR24', 'length': 1},
                'AA': {'name': 'CAN8BITR25', 'length': 1},
                'AB': {'name': 'CAN8BITR26', 'length': 1},
                'AC': {'name': 'CAN8BITR27', 'length': 1},
                'AD': {'name': 'CAN8BITR28', 'length': 1},
                'AE': {'name': 'CAN8BITR29', 'length': 1},
                'AF': {'name': 'CAN8BITR30', 'length': 1},
                'B0': {'name': 'CAN16BITR5', 'length': 2},
                'B1': {'name': 'CAN16BITR6', 'length': 2},
                'B2': {'name': 'CAN16BITR7', 'length': 2},
                'B3': {'name': 'CAN16BITR8', 'length': 2},
                'B4': {'name': 'CAN16BITR9', 'length': 2},
                'B5': {'name': 'CAN16BITR10', 'length': 2},
                'B6': {'name': 'CAN16BITR11', 'length': 2},
                'B7': {'name': 'CAN16BITR12', 'length': 2},
                'B8': {'name': 'CAN16BITR13', 'length': 2},
                'B9': {'name': 'CAN16BITR14', 'length': 2}, 
                'F0': {'name': 'CAN32BITR5', 'length': 4},
                'F1': {'name': 'CAN32BITR6', 'length': 4},
                'F2': {'name': 'CAN32BITR7', 'length': 4},
                'F3': {'name': 'CAN32BITR8', 'length': 4},
                'F4': {'name': 'CAN32BITR9', 'length': 4},
                'F5': {'name': 'CAN32BITR10', 'length': 4},
                'F6': {'name': 'CAN32BITR11', 'length': 4},
                'F7': {'name': 'CAN32BITR12', 'length': 4},
                'F8': {'name': 'CAN32BITR13', 'length': 4},
                'F9': {'name': 'CAN32BITR14', 'length': 4},
                '5A': {'name': 'REP-500', 'length': 4},
                '5B': {'name': 'Refrigeration', 'length': 4},
                '47': {'name': 'EcoDrive and driving style', 'length': 4},
                '5C': {'name': 'PressurePro tires pressure', 'length': 68},
                '5D': {'name': 'DBG-S11Ddosimeter data', 'length': 3},
                'E2': {'name': 'User data 0', 'length': 4},
                'E3': {'name': 'User data 1', 'length': 4},
                'E4': {'name': 'User data 2', 'length': 4},
                'E5': {'name': 'User data 3', 'length': 4},
                'E6': {'name': 'User data 4', 'length': 4},
                'E7': {'name': 'User data 5', 'length': 4},
                'E8': {'name': 'User data 6', 'length': 4},
                'E9': {'name': 'User data 7', 'length': 4},
                'EA': {'name': 'array', 'length': 2},
                '48': {'name': 'Ext_status', 'length': 2},
                '49': {'name': 'tx_channel', 'length': 1},
                'FE': {'name': 'end_1Byte', 'length': 2},

    }
    
    tags_dict_2byte = {
        '0100': {'name': 'Modbus 0', 'length': 4},
        '0200': {'name': 'Modbus 1', 'length': 4},
        '0300': {'name': 'Modbus 2', 'length': 4},
                '0400': {'name': 'Modbus 3', 'length': 4},
                '0500': {'name': 'Modbus 4', 'length': 4},
                '0600': {'name': 'Modbus 5', 'length': 4},
                '0700': {'name': 'Modbus 6', 'length': 4},
                '0800': {'name': 'Modbus 7', 'length': 4},
                '0900': {'name': 'Modbus 8', 'length': 4},
                '0A00': {'name': 'Modbus 9', 'length': 4},
                '0B00': {'name': 'Modbus 10', 'length': 4},
                '0C00': {'name': 'Modbus 11', 'length': 4},
                '0D00': {'name': 'Modbus 12', 'length': 4},
                '0E00': {'name': 'Modbus 13', 'length': 4},
                '0F00': {'name': 'Modbus 14', 'length': 4},
                '1000': {'name': 'Modbus 15', 'length': 4},
                '1100': {'name': 'Modbus 16', 'length': 4},
                '1200': {'name': 'Modbus 17', 'length': 4},
                '1300': {'name': 'Modbus 18', 'length': 4},
                '1400': {'name': 'Modbus 19', 'length': 4},
                '1500': {'name': 'Modbus 20', 'length': 4},
                '1600': {'name': 'Modbus 21', 'length': 4},
                '1700': {'name': 'Modbus 22', 'length': 4},
                '1800': {'name': 'Modbus 23', 'length': 4},
                '1900': {'name': 'Modbus 24', 'length': 4},
                '1A00': {'name': 'Modbus 25', 'length': 4},
                '1B00': {'name': 'Modbus 26', 'length': 4},
                '1C00': {'name': 'Modbus 27', 'length': 4},
                '1D00': {'name': 'Modbus 28', 'length': 4},
                '1E00': {'name': 'Modbus 29', 'length': 4},
                '1F00': {'name': 'Modbus 30', 'length': 4},
                '2000': {'name': 'Modbus 31', 'length': 4},
                '2100': {'name': 'Bluetooth 0', 'length': 4},
                '2200': {'name': 'Bluetooth 1', 'length': 4},
                '2300': {'name': 'Bluetooth 2', 'length': 4},
                '2400': {'name': 'Bluetooth 3', 'length': 4},
                '2500': {'name': 'Bluetooth 4', 'length': 4},
                '2600': {'name': 'Bluetooth 5', 'length': 4},
                '2700': {'name': 'Bluetooth 6', 'length': 4},
                '2800': {'name': 'Bluetooth 7', 'length': 4},
                '2900': {'name': 'Bluetooth 8', 'length': 4},
                '2A00': {'name': 'Bluetooth 9', 'length': 4},
                '2B00': {'name': 'Bluetooth 10', 'length': 4},
                '2C00': {'name': 'Bluetooth 11', 'length': 4},
                '2D00': {'name': 'Bluetooth 12', 'length': 4},
                '2E00': {'name': 'Bluetooth 13', 'length': 4},
                '2F00': {'name': 'Bluetooth 14', 'length': 4},
                '3000': {'name': 'Bluetooth 15', 'length': 4},
                '3100': {'name': 'Bluetooth 16', 'length': 4},
                '3200': {'name': 'Bluetooth 17', 'length': 4},
                '3300': {'name': 'Bluetooth 18', 'length': 4},
                '3400': {'name': 'Bluetooth 19', 'length': 4},
                '3500': {'name': 'Bluetooth 20', 'length': 4},
                '3600': {'name': 'Bluetooth 21', 'length': 4},
                '3700': {'name': 'Bluetooth 22', 'length': 4},
                '3800': {'name': 'Bluetooth 23', 'length': 4},
                '3900': {'name': 'Bluetooth 24', 'length': 4},
                '3A00': {'name': 'Bluetooth 25', 'length': 4},
                '3B00': {'name': 'Bluetooth 26', 'length': 4},
                '3C00': {'name': 'Bluetooth 27', 'length': 4},
                '3D00': {'name': 'Bluetooth 28', 'length': 4},
                '3E00': {'name': 'Bluetooth 29', 'length': 4},
                '3F00': {'name': 'Bluetooth 30', 'length': 4},
                '4000': {'name': 'Bluetooth 31', 'length': 4},
                '4100': {'name': 'Bluetooth 32', 'length': 4},
                '4200': {'name': 'Bluetooth 33', 'length': 4},
                '4300': {'name': 'Bluetooth 34', 'length': 4},
                '4400': {'name': 'Bluetooth 35', 'length': 4},
                '4500': {'name': 'Bluetooth 36', 'length': 4},
                '4600': {'name': 'Bluetooth 37', 'length': 4},
                '4700': {'name': 'Bluetooth 38', 'length': 4},
                '4800': {'name': 'Bluetooth 39', 'length': 4},
                '4900': {'name': 'Bluetooth 40', 'length': 4},
                '4A00': {'name': 'Bluetooth 41', 'length': 4},
                '4B00': {'name': 'Bluetooth 42', 'length': 4},
                '4C00': {'name': 'Bluetooth 43', 'length': 4},
                '4D00': {'name': 'Bluetooth 44', 'length': 4},
                '4E00': {'name': 'Bluetooth 45', 'length': 4},
                '4F00': {'name': 'Bluetooth 46', 'length': 4},
                '5000': {'name': 'Bluetooth 47', 'length': 4},
                '5100': {'name': 'Bluetooth 48', 'length': 4},
                '5200': {'name': 'Bluetooth 49', 'length': 4},
                '5300': {'name': 'Bluetooth 50', 'length': 4},
                '5400': {'name': 'Bluetooth 51', 'length': 4},
                '5500': {'name': 'Bluetooth 52', 'length': 4},
                '5600': {'name': 'Bluetooth 53', 'length': 4},
                '5700': {'name': 'Bluetooth 54', 'length': 4},
                '5800': {'name': 'Bluetooth 55', 'length': 4},
                '5900': {'name': 'Bluetooth 56', 'length': 4},
                '5A00': {'name': 'Bluetooth 57', 'length': 4},
                '5B00': {'name': 'Bluetooth 58', 'length': 4},
                '5C00': {'name': 'Bluetooth 59', 'length': 4},
                '5D00': {'name': 'Bluetooth 60', 'length': 4},
                '5E00': {'name': 'Bluetooth 61', 'length': 4},
                '5F00': {'name': 'Bluetooth 62', 'length': 4},
                '6000': {'name': 'Bluetooth 63', 'length': 4},
                '6100': {'name': 'Modbus 32', 'length': 4},
                '6200': {'name': 'Modbus 33', 'length': 4},
                '6300': {'name': 'Modbus 34', 'length': 4},
                '6400': {'name': 'Modbus 35', 'length': 4},
                '6500': {'name': 'Modbus 36', 'length': 4},
                '6600': {'name': 'Modbus 37', 'length': 4},
                '6700': {'name': 'Modbus 38', 'length': 4},
                '6800': {'name': 'Modbus 39', 'length': 4},
                '6900': {'name': 'Modbus 40', 'length': 4},
                '6A00': {'name': 'Modbus 41', 'length': 4},
                '6B00': {'name': 'Modbus 42', 'length': 4},
                '6C00': {'name': 'Modbus 43', 'length': 4},
                '6D00': {'name': 'Modbus 44', 'length': 4},
                '6E00': {'name': 'Modbus 45', 'length': 4},
                '6F00': {'name': 'Modbus 46', 'length': 4},
                '7000': {'name': 'Modbus 47', 'length': 4},
                '7100': {'name': 'Modbus 48', 'length': 4},
                '7200': {'name': 'Modbus 49', 'length': 4},
                '7300': {'name': 'Modbus 50', 'length': 4},
                '7400': {'name': 'Modbus 51', 'length': 4},
                '7500': {'name': 'Modbus 52', 'length': 4},
                '7600': {'name': 'Modbus 53', 'length': 4},
                '7700': {'name': 'Modbus 54', 'length': 4},
                '7800': {'name': 'Modbus 55', 'length': 4},
                '7900': {'name': 'Modbus 56', 'length': 4},
                '7A00': {'name': 'Modbus 57', 'length': 4},
                '7B00': {'name': 'Modbus 58', 'length': 4},
                '7C00': {'name': 'Modbus 59', 'length': 4},
                '7D00': {'name': 'Modbus 60', 'length': 4},
                '7E00': {'name': 'Modbus 61', 'length': 4},
                '7F00': {'name': 'Modbus 62', 'length': 4},
                '8000': {'name': 'Modbus 63', 'length': 4},
                '8100': {'name': 'Cellid', 'length': 2},
                '8200': {'name': 'LAC', 'length': 2},
                '8300': {'name': 'MCC', 'length': 2},
                '8400': {'name': 'MNC', 'length': 2},
                '8500': {'name': 'RSSI', 'length': 1},
                '8600': {'name': 'TEMPERATURA  0', 'length': 4},
                '8700': {'name': 'TEMPERATURA  1', 'length': 4},
                '8800': {'name': 'TEMPERATURA  2', 'length': 4},
                '8900': {'name': 'TEMPERATURA  3', 'length': 4},
                '8A00': {'name': 'TEMPERATURA  4', 'length': 4},
                '8B00': {'name': 'TEMPERATURA  5', 'length': 4},
                '8C00': {'name': 'TEMPERATURA  6', 'length': 4},
                '8D00': {'name': 'TEMPERATURA  7', 'length': 4},
                '8E00': {'name': 'GPS SATELITE', 'length': 4},
                '8F00': {'name': 'GLONAS', 'length': 4},
                '9000': {'name': 'BAIDOU', 'length': 4},
                '9100': {'name': 'GALI_SAT', 'length': 4},
                '9200': {'name': 'IMSI', 'length': 15},
                '9300': {'name': 'SLOT_SIM', 'length': 1},
                '9400': {'name': 'ICCID', 'length': 20},
                'D900': {'name': 'TMPS 0', 'length': 3},
                'DA00': {'name': 'TMPS 1', 'length': 3},
                'DB00': {'name': 'TMPS 2', 'length': 3},
                'DC00': {'name': 'TMPS 3', 'length': 3},
                'DE00': {'name': 'TMPS 4', 'length': 3},
                'DF00': {'name': 'TMPS 5', 'length': 3},
                'E000': {'name': 'TMPS 6', 'length': 3},
                'E100': {'name': 'TMPS 7', 'length': 3},
                'E200': {'name': 'TMPS 8', 'length': 3},
                'E300': {'name': 'TMPS 9', 'length': 3},
                'E400': {'name': 'TMPS 10', 'length': 3},
                'E500': {'name': 'TMPS 11', 'length': 3},
                'E600': {'name': 'TMPS 12', 'length': 3},
                'E700': {'name': 'TMPS 13', 'length': 3},
                'E800': {'name': 'TMPS 14', 'length': 3},
                'E900': {'name': 'TMPS 15', 'length': 3},
                'EA00': {'name': 'TMPS 16', 'length': 3},
                'EB00': {'name': 'TMPS 17', 'length': 3},
                'EC00': {'name': 'TMPS 18', 'length': 3},
                'ED00': {'name': 'TMPS 19', 'length': 3},
                'EE00': {'name': 'TMPS 20', 'length': 3},
                'Ff00': {'name': 'TMPS 21', 'length': 3},
                'F000': {'name': 'TMPS 22', 'length': 3},
                'F100': {'name': 'TMPS 23', 'length': 3},
                'F200': {'name': 'TMPS 24', 'length': 3},
                'F300': {'name': 'TMPS 25', 'length': 3},
                'F400': {'name': 'TMPS 26', 'length': 3},
                'F500': {'name': 'TMPS 27', 'length': 3},
                'F600': {'name': 'TMPS 28', 'length': 3},
                'F700': {'name': 'TMPS 29', 'length': 3},
                'F800': {'name': 'TMPS 30', 'length': 3},
                'F900': {'name': 'TMPS 31', 'length': 3},
                'FA00': {'name': 'TMPS 32', 'length': 3},
                'FB00': {'name': 'TMPS 33', 'length': 3},
                'FC00': {'name': 'REASON', 'length': 1},
                'FD00': {'name': 'IBUTTOM64', 'length': 4},
                'FE00': {'name': 'IBUTTOM64_2', 'length': 4},
    }

    i = 0
    extracted_tags = []
    use_two_byte_tags = False
    while i < len(tags_data):
        tag = tags_data[i:i+4] if use_two_byte_tags else tags_data[i:i+2]
        i += 4 if use_two_byte_tags else 2
        tag_info = tags_dict_2byte.get(tag) if use_two_byte_tags else tags_dict_1byte.get(tag)
        if tag_info:
            length = tag_info['length'] * 2
            tag_value = tags_data[i:i+length] if length > 0 else ''
            extracted_tags.append((tag_info['name'], tag_value))
            i += length
            if tag == 'FE':
                use_two_byte_tags = True
        
            if tag == "0F":
                if len(tags_data) >= i + 18:  # Asegúrate de que hay suficiente data para 9 bytes
                    coordenadas_hex = tags_data[i:i+18]
                    decodificar_y_dibujar(coordenadas_hex)
        else:
            break
            
    return extracted_tags


def save_frame(frame, frame_type, timestamp, processed_file):
    if len(frame) <= 5:
        return

    if frame[0] == 0x01 and len(frame) >= 5:
        # Formato con cabecera y longitud (como en TCP)
        raw_length = int.from_bytes(frame[1:3], byteorder='little')
        length = raw_length & 0x7FFF

        if length + 3 > len(frame):
            print("[!] Trama UDP incompleta, esperando más datos...")
            return

        frame_body = frame[3:length+3]
    else:
        # No hay cabecera reconocida: eliminar CRC si existe (últimos 2 bytes)
        frame_body = frame[:-2] if len(frame) > 2 else frame

    if len(frame_body) > 48:
        with open(processed_file, "a") as file:
            for i in range(0, len(frame_body), MAX_BYTES):
                block = frame_body[i:i+MAX_BYTES]
                file.write(f"{timestamp},{frame_type},{block.hex().upper()}\n")

        # Extraer tags desde el archivo
        extract_tags_from_file(processed_file)

    
def save_table_to_file():
    with open("tag_parce.txt", "w") as file:
        if table_headers:
            file.write("\t".join(table_headers) + "\n")
        for row in table_data:
            file.write("\t".join(row) + "\n")


def extract_tags_from_file(file_path):
    global table_headers, table_data

    table_headers.clear()
    table_data.clear()

    with open(file_path, "r") as file:
        for line in file:
            parts = line.strip().split(",")
            if len(parts) != 3:
                continue
            timestamp, _, hex_block = parts
            extracted = extract_tags(hex_block)

            if extracted:
                if not table_headers:
                    table_headers = ["Hora"] + [tag[0] for tag in extracted]
                row = [timestamp] + [tag[1] for tag in extracted]
                table_data.append(row)

    save_table_to_file()


def decodificar_y_dibujar(hex_string):
    try:
        raw_bytes = bytes.fromhex(hex_string)
        if len(raw_bytes) < 9:
            print("Trama muy corta:", hex_string)
            return

        byte0 = raw_bytes[0]
        satelites = byte0 & 0x0F
        source = (byte0 >> 4) & 0x0F

        # Invertir bytes (little endian)
        lat_bytes = raw_bytes[1:5][::-1]
        lon_bytes = raw_bytes[5:9][::-1]

        lat = int.from_bytes(lat_bytes, 'big', signed=True) / 1_000_000
        lon = int.from_bytes(lon_bytes, 'big', signed=True) / 1_000_000

        print(f"Coords: Sat: {satelites}, Source: {source}, Lat: {lat}, Lon: {lon}")

        color = "green" if source in (0, 2) else "red"

        coordenadas_mapa.append((lat, lon))

        mapa = folium.Map(location=[lat, lon], zoom_start=14)

        # Dibujar líneas entre puntos consecutivos (NO se une último con primero)
        for i in range(len(coordenadas_mapa) - 1):
            folium.PolyLine([coordenadas_mapa[i], coordenadas_mapa[i+1]], color="blue", weight=4).add_to(mapa)

        # Agregar marcadores individuales
        for idx, (lat_p, lon_p) in enumerate(coordenadas_mapa):
            folium.Marker(
                location=[lat_p, lon_p],
                popup=f"Punto #{idx+1}",
                icon=folium.Icon(color="blue" if idx < len(coordenadas_mapa)-1 else color)
            ).add_to(mapa)

        mapa.save("mapa_coordenadas.html")
        webbrowser.open("mapa_coordenadas.html")

    except Exception as e:
        print(f"Error al procesar coordenadas: {e}")
        


def start_udp_server(host="192.168.0.22", port=2123):
    # Crear un socket UDP
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    print(f"Servidor UDP iniciado en {host}:{port}")

    processed_file = "tramas_procesadas.txt"

    while True:
        try:
            data, address = server.recvfrom(1480)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            print(f"[{timestamp}] Trama recibida desde {address}: {data.hex().upper()}")
            shared_data.last_client_address = address
            
            # Guardar la trama para procesamiento
            save_frame(data, "udp", timestamp, processed_file)
            
            # Construir la respuesta: byte 0x02 seguido de los dos últimos bytes de la trama
            if len(data) >= 2:
                # Obtener los dos últimos bytes del mensaje
                last_two_bytes = data[-2:]
                # Preparar respuesta: 0x02 seguido de los dos últimos bytes
                response = bytes([0x02]) + last_two_bytes
                print(f"[{timestamp}] Enviando respuesta: {response.hex().upper()}")
            else:
                # Si el mensaje tiene menos de 2 bytes, solo enviar 0x02
                response = bytes([0x02])
                print(f"[{timestamp}] Mensaje demasiado corto, enviando respuesta: {response.hex().upper()}")
            
            # Enviar respuesta al cliente
            server.sendto(response, address)
            
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    start_udp_server()