// ============================================================
// XIAO ESP32-S3 + DRV8833 -> N20 geared motor with off-center weight
// Serial-driven haptic alerts (one byte per alert from main.py)
//
//   N  name "Shibu"   one soft tap
//   W  "watch out"    two medium pulses
//   R  "run"          fast triple, twice
//   T  "tsunami"      long-short-long at full power, three times
//   X  stop now
//
// A higher level preempts whatever is playing; a lower one is ignored
// until the current pattern finishes.
//
// D7 / GPIO44 -> DRV8833 IN4
// D8 / GPIO7  -> DRV8833 IN3
// DRV8833 OUT3 -> Motor M1
// DRV8833 OUT4 -> Motor M2
// Common GND
//
// Board: XIAO_ESP32S3, ESP32 Arduino core 3.x.
// Tools -> USB CDC On Boot: Enabled. Otherwise Serial is UART0 on
// GPIO43/44 and fights the motor on D7.
// ============================================================

#define MOTOR_IN4 D7
#define MOTOR_IN3 D8

#define PWM_FREQ 20000
#define PWM_BITS 8

// The N20 gearbox is slow to start and coasts when released, so every pulse
// starts with a full-power kick and every gap starts with an active brake.
#define KICK_MS  50
#define BRAKE_MS 60


void motorForward(uint8_t duty)
{
  // IN3 HIGH/PWM, IN4 LOW
  ledcWrite(MOTOR_IN3, duty);
  ledcWrite(MOTOR_IN4, 0);
}


void motorStop()
{
  ledcWrite(MOTOR_IN3, 0);
  ledcWrite(MOTOR_IN4, 0);
}


void motorBrake()
{
  ledcWrite(MOTOR_IN3, 255);
  ledcWrite(MOTOR_IN4, 255);
}


// ------------------------------------------------------------
// Patterns: {duration ms, duty}. duty 0 = gap. Each ends with a gap so
// the motor is braked before the pattern counts as finished.
// ------------------------------------------------------------

struct Step
{
  uint16_t ms;
  uint8_t duty;
};

const Step PAT_N[] = {
  {200, 150}, {150, 0},
};

const Step PAT_W[] = {
  {250, 190}, {200, 0},
  {250, 190}, {150, 0},
};

const Step PAT_R[] = {
  {150, 230}, {120, 0}, {150, 230}, {120, 0}, {150, 230}, {400, 0},
  {150, 230}, {120, 0}, {150, 230}, {120, 0}, {150, 230}, {150, 0},
};

const Step PAT_T[] = {
  {600, 255}, {150, 0}, {200, 255}, {150, 0}, {600, 255}, {400, 0},
  {600, 255}, {150, 0}, {200, 255}, {150, 0}, {600, 255}, {400, 0},
  {600, 255}, {150, 0}, {200, 255}, {150, 0}, {600, 255}, {150, 0},
};

struct Pattern
{
  char level;
  uint8_t rank;
  const Step *steps;
  uint8_t count;
};

#define LEN(a) (sizeof(a) / sizeof((a)[0]))

const Pattern PATTERNS[] = {
  {'N', 1, PAT_N, LEN(PAT_N)},
  {'W', 2, PAT_W, LEN(PAT_W)},
  {'R', 3, PAT_R, LEN(PAT_R)},
  {'T', 4, PAT_T, LEN(PAT_T)},
};


// ------------------------------------------------------------
// Non-blocking player
// ------------------------------------------------------------

const Pattern *playing = nullptr;
uint8_t stepIdx = 0;
uint32_t stepStart = 0;
int16_t outDuty = -1;  // what the motor is doing now; -1 = braking, -2 = unknown


void setOutput(int16_t duty)
{
  if (duty == outDuty) return;
  outDuty = duty;
  if (duty < 0) motorBrake();
  else if (duty == 0) motorStop();
  else motorForward(duty);
}


void stopAll()
{
  playing = nullptr;
  setOutput(-1);  // brake briefly so the weight stops fast
  delay(BRAKE_MS);
  setOutput(0);
}


// Takes an index, not a Pattern*: the Arduino IDE hoists function prototypes
// above the struct definitions, so custom types can't appear in signatures.
void play(uint8_t i)
{
  const Pattern *p = &PATTERNS[i];
  playing = p;
  stepIdx = 0;
  stepStart = millis();
  outDuty = -2;  // force the first step to be written
  Serial.print("play ");
  Serial.println(p->level);
}


void updatePlayer()
{
  if (!playing) return;

  uint32_t now = millis();
  while (now - stepStart >= playing->steps[stepIdx].ms)
  {
    stepStart += playing->steps[stepIdx].ms;
    if (++stepIdx >= playing->count)
    {
      Serial.print("done ");
      Serial.println(playing->level);
      playing = nullptr;
      setOutput(0);
      return;
    }
  }

  const Step &s = playing->steps[stepIdx];
  uint32_t t = now - stepStart;
  if (s.duty > 0) setOutput(t < KICK_MS ? 255 : s.duty);
  else setOutput(t < BRAKE_MS ? -1 : 0);
}


void handleByte(char c)
{
  if (c == 'X')
  {
    stopAll();
    Serial.println("stop");
    return;
  }
  for (uint8_t i = 0; i < LEN(PATTERNS); i++)
  {
    if (PATTERNS[i].level != c) continue;
    if (playing && PATTERNS[i].rank < playing->rank)
    {
      Serial.print("ignored ");
      Serial.println(c);
      return;
    }
    play(i);
    return;
  }
  // anything else (\r, \n, noise) is ignored
}


void setup()
{
  Serial.begin(115200);

  // ESP32 Arduino Core 3.x
  ledcAttach(MOTOR_IN3, PWM_FREQ, PWM_BITS);
  ledcAttach(MOTOR_IN4, PWM_FREQ, PWM_BITS);

  setOutput(0);

  Serial.println("SVL haptic ready: N W R T, X = stop");
}


void loop()
{
  while (Serial.available() > 0)
    handleByte((char)Serial.read());

  updatePlayer();
}
