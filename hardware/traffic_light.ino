/*
 * =============================================================
 *  Traffic-Mind: Arduino Traffic Light Controller
 *  Controls 4 sets of RGB LEDs + reads 4 IR sensors
 * =============================================================
 *
 * WIRING
 * ------
 * North Traffic Light:  Pin 2 = Red, Pin 3 = Yellow, Pin 4 = Green
 * South Traffic Light:  Pin 5 = Red, Pin 6 = Yellow, Pin 7 = Green
 * East  Traffic Light:  Pin 8 = Red, Pin 9 = Yellow, Pin 10 = Green
 * West  Traffic Light:  Pin 11= Red, Pin 12= Yellow, Pin 13= Green
 *
 * IR Sensors (optional):
 *   A0 = North, A1 = South, A2 = East, A3 = West
 *
 * PROTOCOL (from Python via Serial @ 9600 baud)
 * ------------------------------------------------
 *   '0'  →  NS Green, EW Red
 *   '1'  →  EW Green, NS Red
 *   '2'  →  All Yellow
 *   '3'  →  All Red
 *   '9'  →  Send sensor data back
 */

// ── Pin definitions ──────────────────────────

// North
const int N_RED = 2;
const int N_YEL = 3;
const int N_GRN = 4;

// South
const int S_RED = 5;
const int S_YEL = 6;
const int S_GRN = 7;

// East
const int E_RED = 8;
const int E_YEL = 9;
const int E_GRN = 10;

// West
const int W_RED = 11;
const int W_YEL = 12;
const int W_GRN = 13;

// IR sensor analog pins
const int SENSOR_N = A0;
const int SENSOR_S = A1;
const int SENSOR_E = A2;
const int SENSOR_W = A3;

const int IR_THRESHOLD = 500;  // analog value above which = "car present"

// ── Helper: set one traffic light ────────────
void setLight(int redPin, int yelPin, int grnPin, char state) {
    digitalWrite(redPin, LOW);
    digitalWrite(yelPin, LOW);
    digitalWrite(grnPin, LOW);

    switch (state) {
        case 'R': digitalWrite(redPin, HIGH); break;
        case 'Y': digitalWrite(yelPin, HIGH); break;
        case 'G': digitalWrite(grnPin, HIGH); break;
    }
}

// ── Phase helpers ────────────────────────────
void setPhase_NS_Green() {
    setLight(N_RED, N_YEL, N_GRN, 'G');
    setLight(S_RED, S_YEL, S_GRN, 'G');
    setLight(E_RED, E_YEL, E_GRN, 'R');
    setLight(W_RED, W_YEL, W_GRN, 'R');
}

void setPhase_EW_Green() {
    setLight(N_RED, N_YEL, N_GRN, 'R');
    setLight(S_RED, S_YEL, S_GRN, 'R');
    setLight(E_RED, E_YEL, E_GRN, 'G');
    setLight(W_RED, W_YEL, W_GRN, 'G');
}

void setPhase_AllYellow() {
    setLight(N_RED, N_YEL, N_GRN, 'Y');
    setLight(S_RED, S_YEL, S_GRN, 'Y');
    setLight(E_RED, E_YEL, E_GRN, 'Y');
    setLight(W_RED, W_YEL, W_GRN, 'Y');
}

void setPhase_AllRed() {
    setLight(N_RED, N_YEL, N_GRN, 'R');
    setLight(S_RED, S_YEL, S_GRN, 'R');
    setLight(E_RED, E_YEL, E_GRN, 'R');
    setLight(W_RED, W_YEL, W_GRN, 'R');
}

// ── Sensor reading ───────────────────────────
void readAndSendSensors() {
    int nVal = analogRead(SENSOR_N) > IR_THRESHOLD ? 1 : 0;
    int sVal = analogRead(SENSOR_S) > IR_THRESHOLD ? 1 : 0;
    int eVal = analogRead(SENSOR_E) > IR_THRESHOLD ? 1 : 0;
    int wVal = analogRead(SENSOR_W) > IR_THRESHOLD ? 1 : 0;

    // Send formatted string
    Serial.print("N:");
    Serial.print(nVal);
    Serial.print(",S:");
    Serial.print(sVal);
    Serial.print(",E:");
    Serial.print(eVal);
    Serial.print(",W:");
    Serial.println(wVal);
}

// ── Setup ────────────────────────────────────
void setup() {
    // LED pins
    for (int pin = 2; pin <= 13; pin++) {
        pinMode(pin, OUTPUT);
    }

    // Sensor pins
    pinMode(SENSOR_N, INPUT);
    pinMode(SENSOR_S, INPUT);
    pinMode(SENSOR_E, INPUT);
    pinMode(SENSOR_W, INPUT);

    Serial.begin(9600);

    // Start with all red
    setPhase_AllRed();
}

// ── Main loop ────────────────────────────────
void loop() {
    if (Serial.available() > 0) {
        char cmd = Serial.read();

        switch (cmd) {
            case '0': setPhase_NS_Green();      break;
            case '1': setPhase_EW_Green();      break;
            case '2': setPhase_AllYellow();     break;
            case '3': setPhase_AllRed();        break;
            case '9': readAndSendSensors();     break;
            default: break;
        }
    }
}
