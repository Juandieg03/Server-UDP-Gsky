import socket
import sys

def main():
    # Configuración del servidor
    UDP_IP = "192.168.0.22"  # Dirección IP para escuchar
    UDP_PORT = 2123          # Puerto para escuchar
    
    try:
        # Crear un socket UDP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Enlazar el socket a la dirección y puerto especificados
        sock.bind((UDP_IP, UDP_PORT))
        
        print(f"Servidor UDP iniciado en {UDP_IP}:{UDP_PORT}")
        print("Esperando tramas...")
        
        while True:
            # Recibir datos (hasta 1024 bytes)
            data, addr = sock.recvfrom(1480)
            print(f"Recibido mensaje desde {addr[0]}:{addr[1]}")
            print(f"Mensaje: {data.hex()}")
            
            if len(data) >= 2:
                # Obtener los dos últimos bytes del mensaje
                last_two_bytes = data[-2:]
                # Preparar respuesta: 0x02 seguido de los dos últimos bytes
                response = bytes([0x02]) + last_two_bytes
                print(f"Enviando respuesta: {response.hex()}")
            else:
                # Si el mensaje tiene menos de 2 bytes, solo enviar 0x02
                response = bytes([0x02])
                print(f"Mensaje demasiado corto, enviando respuesta: {response.hex()}")
            
            # Enviar respuesta al cliente
            sock.sendto(response, addr)
            
    except socket.error as e:
        print(f"Error de socket: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario")
        sock.close()
        sys.exit(0)
    except Exception as e:
        print(f"Error inesperado: {e}")
        sock.close()
        sys.exit(1)
    finally:
        sock.close()

if __name__ == "__main__":
    main()