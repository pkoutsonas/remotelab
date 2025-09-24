from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import random
import serial
import time
import nidaqmx

app = Flask(__name__)
CORS(app)

PORT = "/dev/tty.usbmodem1201"  # Θύρα που χρησημοποιείται από το Mac
BAUD_RATE = 9600

# Κατάσταση ρελέ
relay_state = {f"relay{i}": False for i in range(1, 9)}

# Προσπαθούμε να συνδεθούμε στο Arduino
try:
    print(f"🔌 Προσπάθεια σύνδεσης με Arduino στο {PORT}...")
    arduino = serial.Serial(PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Περιμένουμε την αρχικοποίηση
    print("✅ Arduino συνδέθηκε επιτυχώς!")
except serial.SerialException as e:
    print(f"❌ Σφάλμα σύνδεσης με το Arduino: {e}")
    arduino = None

@app.route('/test_arduino')
def test_arduino():
    """ Δοκιμή σύνδεσης με το Arduino """
    if isinstance(arduino):
        return jsonify({"status": "error", "message": "Mock mode active, no real Arduino connected"}), 500

    try:
        arduino.write(b'PING\n')
        time.sleep(0.5)
        response = arduino.readline().decode().strip()

        if response == "PONG":
            return jsonify({"status": "success", "message": "Arduino είναι συνδεδεμένο"})
        else:
            return jsonify({"status": "error", "message": f"Unexpected response: {response}"}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def read_voltage():
    """ Διαβάζει την τάση από το NI myDAQ στο κανάλι ai0 """
    try:
        with nidaqmx.Task() as task:
            task.ai_channels.add_ai_voltage_chan("Dev1/ai0")  
            voltage = task.read()
            print(f"✅ Επιτυχία ανάγνωσης από το NI myDAQ: {voltage}")
            return round(voltage, 3)
    except Exception as e:
        print(f"❌ Σφάλμα ανάγνωσης από το NI myDAQ: {e}")
        return None

def get_voltage():
    """ Mock voltage value """
    return round(random.uniform(0, 5), 2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/voltage')
def voltage():
    value = get_voltage()
    voltage_data = {
        "timestamp": time.time(),
        "voltage": value if value is not None else 0
    }
    return jsonify(voltage_data)



@app.route('/toggle_relay/<int:relay_id>', methods=['POST'])
def toggle_specific_relay(relay_id):
    if relay_id not in range(1, 9):  # Ελέγχει ότι το relay ID είναι σωστό
        return jsonify({'error': 'Invalid relay ID'}), 400

    # Εναλλαγή της κατάστασης του ρελέ
    relay_state[f"relay{relay_id}"] = not relay_state[f"relay{relay_id}"]
    command = f"{relay_id}:{'ON' if relay_state[f'relay{relay_id}'] else 'OFF'}\n"

    try:
        # Εντολή στο Arduino
        arduino.write(command.encode())
        time.sleep(0.5)  # Μικρή καθυστέρηση για ανταπόκριση
        response = arduino.readline().decode().strip()

        print(f"➡️ Εντολή προς Arduino: {command.strip()}")
        print(f"⬅️ Απάντηση Arduino: {response}")

        return jsonify({
            'success': True,
            'relay': relay_id,
            'state': relay_state[f"relay{relay_id}"]
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
