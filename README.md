# BJT Common-Emitter — Lab 03 DC Bias และ Lab 04 CE Amplifier Simulator

งานส่งวิชา ENG29 2121: เว็บแอป Flask ที่เริ่มจากเครื่องคำนวณจุดทำงาน DC ของสเตจ
common-emitter สำหรับ **วงจรไบอัส 3 แบบ** แจ้งเตือนเมื่อไบอัสอยู่นอกช่วง
forward-active และตรวจผลทุกโหมดด้วยการแก้สมการ nodal อีกวิธีหนึ่งอย่างอิสระ
จากนั้น Lab 04 ต่อยอดด้วยหน้า simulator ที่รัน ngspice จริงสำหรับวงจร
voltage-divider common-emitter หนึ่งวงจร (DC, AC และ transient)

- **Voltage Divider Bias** — ค่าเหมือน Lab 02 ทุกตัวเลข
- **Fixed Bias** — มีตัวต้านทานที่ฐานตัวเดียว
- **Emitter Bias (single supply)** — มีตัวต้านทานที่ฐานและที่อิมิตเตอร์

## Repository

- GitHub: <https://github.com/naphataphichai-cmd/Lab3>
- Commit ของ Lab 03: `27700bba838c487dfb7dafb3491bb2f3bd2c2536`
- วิธีรันและเปิดเว็บ: ดูหัวข้อ [วิธีรัน](#วิธีรัน)

## หลักการทำงาน

เลือกโหมดวงจรก่อน แล้วกรอก `VCC, RC, β, VBE` พร้อมตัวต้านทานที่โหมดนั้นใช้จริง

| โหมด | อินพุตเพิ่มเติม | ตำแหน่งตัวต้านทาน |
|---|---|---|
| Fixed Bias | `RB` | `RB` จาก VCC ไปฐาน, อิมิตเตอร์ต่อลงกราวด์ |
| Emitter Bias | `RB, RE` | `RB` จาก VCC ไปฐาน, `RE` จากอิมิตเตอร์ลงกราวด์ |
| Voltage Divider | `R1, R2, RE` | `R1` VCC→ฐาน, `R2` ฐาน→กราวด์, `RE` อิมิตเตอร์→กราวด์ |

ทุกช่องมีตัวเลือกหน่วยของตัวเอง (`Ω` / `kΩ` / `MΩ` สำหรับตัวต้านทาน และ
`V` / `mV` สำหรับแรงดัน) จึงกรอกค่าตามที่เขียนในใบงานได้เลย ผลลัพธ์ที่ได้คือ

- `IB, IC, IE` ในหน่วย µA / mA / A
- `VCE, VB, VE, VC` ในหน่วยโวลต์
- ภาคการทำงาน: `cutoff`, `active` หรือ `saturation`
- ข้อความแจ้งข้อผิดพลาดรายช่องเมื่ออินพุตไม่ถูกต้อง
- ตารางเทียบค่าจากการคำนวณสองวิธี (analytical กับ nodal)

หน้าเว็บแบ่งเป็น 3 ส่วน: ฟอร์มอินพุตด้านซ้าย, แผนภาพวงจรของโหมดที่เลือก
(พร้อมค่าอุปกรณ์ที่กรอก) ตรงกลาง และจุดทำงาน DC ด้านขวา เมื่อเลือกโหมด
หน้าเว็บจะโหลดใหม่ทันทีด้วยช่องอินพุตของวงจรนั้น ถ้าปิด JavaScript ไว้จะมีปุ่ม
"Load circuit" ให้กดส่งฟอร์มแทน โหมด Voltage Divider ยังแสดง `R1`, `R2`
และ `RE` เหมือน Lab 02 ทุกประการ

ทั้งสามโหมดคืนค่าเป็น `model.OperatingPoint` ชุดเดียวกับ Lab 02 (ฟิลด์
`vb, ve, vc, vce, ib, ic, ie`) ชั้นเปรียบเทียบผลและการจัดรูปแบบหน่วยจึงใช้ร่วมกัน
ได้ทั้งหมด แต่ละฟังก์ชันคืนค่า `rb` ของโหมดนั้นด้วย และคืน `vbb` เฉพาะโหมด
divider หน่วยผลลัพธ์ถูกกำหนดโดย `engineering/format.py` (โวลต์ และ A/µA/mA)
ทุกโหมดจึงรายงานหน่วยเดียวกัน

ตัวอย่างเริ่มต้นของโหมด divider คือ 12 V, 100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ,
β = 100, VBE = 0.70 V ให้ผลประมาณ `IB = 12.3 µA`, `IC = 1.23 mA` และ
`VCE = 8.052 V` ซึ่งเป็นค่าเดิมของ Lab 02

## เส้นทางการคำนวณ (analytical)

`engineering/solver.py` เก็บเส้นทาง Thévenin ของ Lab 02 ไว้ และเพิ่มฟังก์ชัน
อีกหนึ่งตัวต่อโหมดใหม่

Voltage Divider (ไม่แก้ไข):

```text
VBB = VCC · R2 / (R1 + R2)
RB  = R1 · R2 / (R1 + R2)
IB  = (VBB − VBE) / (RB + (β + 1)·RE)
```

Fixed:

```text
IB = (VCC − VBE) / RB
VE = 0
```

Emitter (single supply):

```text
IB = (VCC − VBE) / [RB + (β + 1)·RE]
VE = IE · RE
```

ชั้นเอาต์พุตที่ใช้ร่วมกัน:

```text
IC  = β · IB
IE  = (β + 1) · IB
VC  = VCC − IC · RC
VB  = VE + VBE
VCE = VC − VE
```

## การตรวจสอบอิสระ (nodal cross-check)

`engineering/crosscheck.py` ไม่ได้ใช้สมการ closed-form ชุดเดียวกับด้านบน
แต่เขียนสมการที่โหนด (KCL) ของแต่ละโหมดแล้วแก้ด้วยการกำจัดตัวแปรแบบเกาส์
พร้อม partial pivoting

- **Divider** — ตัวแปรที่แก้ `VB, VE, VC`:
  ```text
  −(1/R1 + 1/R2)·VB − (1/((β+1)·RE))·VE = −VCC/R1
  −(β/((β+1)·RE))·VE − (1/RC)·VC        = −VCC/RC
  VB − VE                                = VBE
  ```
- **Fixed** — ตัวแปรที่แก้ `VB, VC, IB`:
  ```text
  (1/RB)·VB + IB          = VCC/RB
  (1/RC)·VC + β·IB        = VCC/RC
  VB                      = VBE
  ```
- **Emitter** — ตัวแปรที่แก้ `VB, VE, VC`: สมการฐานแบบ divider โดยเปลี่ยน
  `1/R1 + 1/R2` เป็น `1/RB`

ผลจากสองเส้นทางถูกเทียบทีละฟิลด์ด้วยค่าคลาดเคลื่อนสัมพัทธ์ `1e-6`
หน้าเว็บแสดงทั้งสองคอลัมน์พร้อมค่าคลาดเคลื่อนสัมพัทธ์สูงสุด

## กติกาภาคการทำงาน

- **Cutoff** — เมื่อแก้ได้ `IB <= 0` โหมด divider จะสร้างผลลัพธ์ cutoff ทางกายภาพ
  ให้ (`model.py`) ส่วนโหมดใหม่จะเก็บค่าดิบไว้และแสดงคำเตือน เพราะด้วยอินพุตที่
  ถูกต้อง (`VBE < VCC`) โหมด Fixed และ Emitter ไปถึง cutoff ไม่ได้ในแบบจำลองนี้
- **Saturation** — เมื่อ `VCE <= 0.2 V` หน้าเว็บแสดงค่าดิบตามที่คำนวณได้
  (รวมถึง `VCE` ที่ติดลบถ้าแบบจำลองให้ค่าเช่นนั้น) พร้อมคำเตือนว่าจุดทำงานนี้ใช้เป็น
  แอมพลิฟายเออร์ไม่ได้ ไม่มีการตัดค่า (clamp) ใด ๆ
- **Active** — กรณีอื่นทั้งหมด จะมีหมายเหตุเรื่องกระแสฐานต่ำเมื่อ `IB < 1 µA`

## การตรวจสอบอินพุต

ระบบจะบังคับกรอกและแปลงหน่วยเฉพาะช่องที่โหมดที่เลือกใช้เท่านั้น ทุกช่องที่ใช้ต้อง
เป็นจำนวนจำกัด (finite) หน่วยที่เลือกจะถูกแปลงเป็นโอห์มและโวลต์ที่ขอบนอกของแอป
ชั้นคำนวณจึงเห็นเฉพาะหน่วยฐานเสมอ ช่วงค่าที่รับได้:

| ช่อง | ช่วงที่รับ |
|---|---|
| `VCC` | `0 < VCC <= 100 V` |
| `RB, R1, R2, RC, RE` | `1 mΩ <= R <= 10 MΩ` |
| `β` | `1 < β <= 2000` |
| `VBE` | `0 <= VBE < VCC` |

ถ้าโหมดที่ส่งมาไม่รู้จัก ระบบจะแจ้งข้อผิดพลาดแทนที่จะถือว่าเป็น divider
เมื่ออินพุตไม่ถูกต้อง หน้าเว็บจะแสดงฟอร์มเดิมพร้อมค่าที่กรอกไว้ ข้อความแจ้งข้างช่อง
นั้น และไม่มีผลลัพธ์จากการรันครั้งก่อนค้างอยู่ ถ้าผลลัพธ์กลางทางไม่ใช่ค่าจำกัด
ระบบจะรายงานเป็นข้อผิดพลาดปกติ ไม่ใช่ error 500

## Lab 04 — CE Amplifier Simulator (ngspice)

Lab 04 ไม่ได้แทนที่ Lab 03: หน้า `/` และผลคำนวณ DC ทั้งสามโหมดยังทำงานเหมือนเดิม
ส่วนหน้า `/simulator` เพิ่มการจำลองวงจร common-emitter แบบ voltage divider
หนึ่งวงจรด้วย ngspice จริง

### สิ่งที่หน้า `/simulator` ทำ

- รับ `VCC, R1, R2, RC, RE, RL, Cin, Cout` และแหล่งจ่าย `amplitude, frequency`
  พร้อมหน่วย `V/mV`, `Ω/kΩ/MΩ`, `pF/nF/µF/F` และ `Hz/kHz/MHz`
- **DC (`.op`)** — รายงาน `VB, VE, VC, VCE, IC, IB, IE` จาก ngspice
  พร้อมภาคการทำงานและคำเตือนเมื่อ `VCE ≤ 0.2 V` หรือ `IC ≤ 0`
- **AC (`.ac`)** — sweep คงที่ `0.1 Hz – 100 MHz` (20 จุด/decade) วาดกราฟ Bode
  ของขนาดเกน (dB) และเฟส (องศา) รายงานเกน/เฟสที่ความถี่แหล่งจ่าย มิดแบนด์เกน
  และจุดตัด `−3 dB` (ถ้าอยู่นอกช่วง sweep จะเขียนว่า "not determined in sweep range")
- **Transient (`.tran`)** — จำลอง 5 คาบของแหล่งจ่าย จำกัดช่วง `10 µs – 50 ms`
  วาด `Vin` กับ `Vout` ตามเวลา รายงานค่า peak-to-peak, อัตราส่วน และทิศทางการกลับเฟส
- แสดง `ngspice-47`, โมเดล `2N3904`, netlist ที่ส่งจริง, log ของ ngspice
  และสถานะการรัน
- แสดงผล Lab 03 analytical (`β = 100`, `VBE = 0.70 V`) เทียบข้าง ๆ ในคอลัมน์
  `Lab 03` และ `|Δ|` โดยระบุชัดว่าผล SPICE กับ analytical ใช้สมมติฐานต่างกัน
  จึงไม่จำเป็นต้องตรงกันทุกหลัก

### ติดตั้ง ngspice (Windows)

แอปเรียก ngspice เป็น executable ภายนอก ไม่ได้ติดตั้งผ่าน pip วิธีที่ใช้ในแล็บนี้:

1. ดาวน์โหลด `ngspice-47_64.7z` จาก
   <https://sourceforge.net/projects/ngspice/files/ng-spice-rework/47/>
2. แตกไฟล์ไว้ที่ `tools/ngspice/` ให้ได้ path
   `tools/ngspice/Spice64/bin/ngspice_con.exe`
3. ถ้าเก็บไว้ที่อื่น ให้ตั้ง environment variable `NGSPICE_BIN` ชี้ไปที่ไฟล์ `.exe`
   หรือเพิ่มโฟลเดอร์ `bin` ของ ngspice ลง `PATH`

โฟลเดอร์ `tools/` ถูก ignore ใน git เพราะเป็นไฟล์ไบนารีของเครื่องนี้
ถ้าไม่พบ ngspice หน้าเว็บจะแสดง error ที่อ่านได้และไม่ค้างผลรันครั้งก่อนไว้

### โมเดลและความโปร่งใสของผล

- โมเดล BJT คือ Motorola 2N3904 Gummel-Poon card มาตรฐาน
  (`IS=6.734f ... BF=416.4 ...`) การ์ดเต็มปรากฏใน netlist บนหน้าเว็บ
- ทุกจุดของกราฟมาจากไฟล์ `ac.txt` / `tran.txt` ที่ ngspice เขียนจริง
  ไม่มี trace จำลองหรือค่าคงที่ที่ hard-code
- ช่วงอินพุต: `0 < VCC ≤ 100 V`, `1 mΩ ≤ R ≤ 10 MΩ`, `1 pF ≤ C ≤ 1 F`,
  `0 < amplitude ≤ 1 V peak`, `1 Hz ≤ frequency ≤ 10 MHz`
- ทุกค่าถูกแปลงเป็นหน่วยฐานและตรวจว่าเป็นจำนวนจำกัดก่อนสร้าง netlist
  ข้อความจากฟอร์มไม่ถูกส่งเข้า netlist หรือ command line โดยตรง
- ใช้ `subprocess.run` แบบ argument list, `shell=False`, มี timeout และ
  working directory ชั่วคราวแยกต่อการรัน

### ค่าอ้างอิงของวงจรตั้งต้น

`VCC = 12 V`, `R1 = 100 kΩ`, `R2 = 22 kΩ`, `RC = 2.2 kΩ`, `RE = 1 kΩ`,
`RL = 10 kΩ`, `Cin = Cout = 10 µF`, `amplitude = 10 mV peak`, `frequency = 1 kHz`
ให้ผลจาก ngspice 47 กับโมเดล 2N3904 ประมาณ:

| Analysis | Observed |
|---|---|
| DC | `VB = 2.004 V`, `VE = 1.333 V`, `VC = 9.087 V`, `VCE = 7.754 V`, `IB = 8.887 µA`, `IC = 1.324 mA`, `IE = 1.333 mA` (active) |
| AC @ 1 kHz | `4.89 dB (1.756×)`, phase `−179.9°`, midband `4.89 dB`; `fL ≈ 2 Hz`, `fH` อยู่นอก sweep |
| Transient | `Vin pp = 20 mV`, `Vout pp = 35.1 mV`, `1.76×`, inverted (≈180°), window `0 – 5 ms` |

ค่าเหล่านี้เป็นผลจาก simulator ไม่ใช่ค่าที่คำนวณมือ และใช้เป็น baseline
ของ browser acceptance B2–B6 ใน `docs/validation.md`

### เทสต์ของ Lab 04

- `tests/test_spice_engine.py` — netlist, parser, error path และ integration test
  ที่รัน ngspice จริง (จะ skip เมื่อไม่พบ engine)
- `tests/test_spice_validation.py` — ช่วงอินพุตและ choice ของ analysis
- `tests/test_plotting.py` — SVG ของ Bode และ transient
- `tests/test_simulator_routes.py` — route และ view model รวมถึงกรณี error
  ที่ต้องไม่แสดงผลรันเก่าค้างไว้

ชุดเทสต์ Lab 03 ทั้งหมดยังต้องผ่านพร้อมกัน

## วิธีรัน

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m flask --app app run --port 5000
```

เปิด <http://127.0.0.1:5000/> สำหรับ Lab 03 หรือ
<http://127.0.0.1:5000/simulator> สำหรับ Lab 04 และเปิดตรงเข้าที่โหมดที่ต้องการได้
เช่น `http://127.0.0.1:5000/?mode=fixed` (หรือเลือกโหมดในหน้าเว็บก็ได้)
หน้า Lab 04 ต้องมี ngspice ตามหัวข้อติดตั้งด้านบนก่อนจึงจะรันได้

## วิธีทดสอบ

```powershell
.\.venv\Scripts\python -m pytest -q
```

เทสต์ integration ของ Lab 04 จะรัน ngspice จริงเมื่อพบ executable
และจะถูก skip พร้อมเหตุผลเมื่อเครื่องยังไม่ได้ติดตั้ง ngspice

## โครงสร้างโปรเจกต์

```text
app.py                      Flask factory, Lab 03 routes, Lab 04 /simulator, การแปลงหน่วย
engineering/
  model.py                  ชื่อโหมด, dataclass ของอินพุต, กติกาภาคการทำงาน, display point
  solver.py                 เส้นทาง analytical: divider (Thévenin), fixed, emitter
  crosscheck.py             เส้นทาง nodal อิสระ + การกำจัดตัวแปรแบบเกาส์
  evaluate.py               เลือกเส้นทางตามโหมดและสร้างผลเปรียบเทียบ
  validation.py             การอ่านค่าและกติกาอินพุตแยกตามโหมด
  compare.py                การเทียบผลด้วยค่าคลาดเคลื่อนที่ยอมรับได้
  format.py                 แปลงค่า → (ตัวเลข, หน่วย)
spice_engine.py             netlist, ngspice subprocess, parser, provenance
spice_validation.py         ช่วงอินพุตของ simulator และการเลือก analysis
plotting.py                 SVG ของ Bode และ transient (ไม่ใช้ JS chart library)
templates/                  base, index (Lab 03) และ simulator (Lab 04)
static/style.css            สไตล์แบบ lab sheet + simulator layout
tests/                      เทสต์ระดับหน่วย, route และ ngspice integration
docs/validation.md          ผลตรวจ A1–A5 ของ Lab 03 และ B1–B8 ของ Lab 04
docs/superpowers/           เอกสารออกแบบและแผนงานที่อนุมัติแล้ว
tools/                      ngspice ที่ติดตั้งในเครื่อง (gitignored)
```

## ผลตรวจ A1–A5 และ B1–B8

`docs/validation.md` เก็บตาราง A1–A5 ของ Lab 03 พร้อมค่าคาดหมายที่คำนวณมือ
แยกต่างหาก ผลที่อ่านได้จากหน้าเว็บจริง และวิธีที่ใช้ตรวจ ทั้ง 5 กรณีรันใน
เบราว์เซอร์ของแอปและผ่านทั้งหมด โดย `docs/lab03-a3-emitter.jpeg` คือภาพหน้าเว็บ
กรณี A3 ส่วนชุดเทสต์ก็ครอบตัวเลขชุดเดียวกันทั้งในระดับ Python และระดับ route

ส่วน Lab 04 มีตาราง B1–B8 ในไฟล์เดียวกัน ครอบการถดถอยของ Lab 03, DC/AC/tran
จาก ngspice จริง, การเปลี่ยน `RE`, การเปลี่ยนแหล่งจ่าย, อินพุตผิด (`RE = 0`)
และ layout ที่ความกว้างเดสก์ท็อปกับมือถือ ค่าที่อ่านได้และข้อจำกัดของหลักฐาน
(เช่น screenshot ที่ถูกบล็อกเพราะหน้าต่างเบราว์เซอร์ไม่แสดง) ถูกบันทึกตามจริง
ในตาราง

## คำชี้แจงการใช้ AI

งาน Lab 03 นี้พัฒนาด้วย **OpenCode (AI coding assistant)** ภายใต้การกำกับของ
ผู้เขียน นักศึกษาเป็นผู้ให้โจทย์ใบงาน เลือกโหมดทั้งสามและกำหนดเงื่อนไข (ค่าโหมด
divider ต้องเท่า Lab 02, โหมดใหม่ให้เตือนแทนการแก้ค่า cutoff/saturation,
วิเคราะห์เฉพาะ DC operating point) และตรวจทานทุกการเปลี่ยนแปลงก่อน commit
หัวข้อด้านล่างระบุชัดเจนว่า AI สร้างอะไร นักศึกษาตรวจอะไร และโค้ดเลือกโหมดกับ
แปลงหน่วยอยู่ตรงไหน

### สมการและหน่วยที่ใช้

ชั้นคำนวณใช้เฉพาะ **โอห์มและโวลต์** ทุกโหมดแก้สเตจเอาต์พุตชุดเดียวกัน คือ
`IC = β·IB`, `IE = (β + 1)·IB`, `VC = VCC − IC·RC`, `VB = VE + VBE`,
`VCE = VC − VE` (กระแสเป็น A, แรงดันเป็น V, ความต้านทานเป็น Ω)

- **Voltage divider** (เส้นทางเดิมของ Lab 02):
  `VBB = VCC·R2/(R1 + R2)`, `RB = R1·R2/(R1 + R2)`,
  `IB = (VBB − VBE)/(RB + (β + 1)·RE)`
- **Fixed bias:** `IB = (VCC − VBE)/RB`, `VE = 0`, `VCE = VC`
- **Emitter bias (single supply):** `IB = (VCC − VBE)/(RB + (β + 1)·RE)`,
  `IE = (β + 1)·IB`, `VE = IE·RE`

หน่วยที่แสดงผลสร้างจาก `engineering/format.py`: กระแสเป็น µA เมื่อต่ำกว่า 1 mA,
เป็น mA เมื่อต่ำกว่า 1 A นอกนั้นเป็น A; แรงดันเป็น V; ความต้านทานเป็น Ω/kΩ/MΩ
การคำนวณมือของ A1–A5 ใน `docs/validation.md` ใช้สมการและหน่วยชุดเดียวกันนี้

### ส่วนที่ AI สร้าง

- `engineering/solver.py` — `solve_fixed()` และ `solve_emitter()` (ฟังก์ชัน
  `solve()` ของ divider คงไว้เหมือนเดิมทุกบรรทัด)
- `engineering/crosscheck.py` — ระบบสมการ nodal อิสระของ fixed (`VB, VC, IB`)
  และ emitter (`VB, VE, VC`) ที่แก้ด้วย `gaussian_solve()` เดิม
- `engineering/evaluate.py` — `_paths()` สำหรับเลือกเส้นทางตามโหมด และฟิลด์
  `mode` ใน `Evaluation`; `engineering/model.py` — ค่าคงที่ของโหมด,
  `FixedBiasInputs`, `EmitterBiasInputs` และพารามิเตอร์ `mode` ของ `display_point()`
- `engineering/validation.py` — `MODE_FIELDS`, `parse_mode()`,
  `parse_inputs_for_mode()` และกติกาช่วงค่าที่ใช้ร่วมกัน
- `app.py` — ค่าเริ่มต้น/หน่วยของ `rb`, `MODE_CHOICES`, การแปลงหน่วยและการส่งต่อ
  ตามโหมด, การสร้างผลลัพธ์ และข้อมูล `ACCEPTANCE_CASES`
- `templates/index.html`, `templates/base.html`, `static/style.css` — ตัวเลือกโหมด,
  ช่องอินพุตที่แสดงตามโหมด, แผนภาพ SVG ของแต่ละโหมด และตารางผลตรวจ A1–A5
- `tests/test_modes.py` และเทสต์อีกสองตัวใน `tests/test_routes.py` — เทสต์ของ
  solver, crosscheck, validation, route และตารางผลตรวจของโหมดใหม่

### สิ่งที่นักศึกษาตรวจ

ผู้เขียนคำนวณ A1–A5 ด้วยมือจากสมการข้างต้น **ก่อน** รันแอป (ดู
`docs/validation.md`) แล้วรันแต่ละกรณีในเบราว์เซอร์และเทียบผล: `IC` ต่างได้ไม่เกิน
±0.01 mA และ `VCE` ต่างได้ไม่เกิน ±0.02 V ตรวจว่า A4 (`RE = 2 kΩ`) ให้ `IC`
ต่ำกว่า A3, A5 (`RB = 0`) ขึ้นข้อความช่วงค่าและตารางผลว่างโดยไม่มีป้าย `MATCH`,
โหมด divider ค่าเริ่มต้นยังได้ค่าเดิมของ Lab 02 (`IB = 12.3 µA`, `IC = 1.23 mA`,
`VCE = 8.052 V`), การเลือกโหมดวาดวงจรใหม่ถูกต้องทันที และแผนภาพที่แสดงตรงกับ
โหมดที่เลือก นอกจากนี้ยังตรวจสมการ nodal ของ cross-check เทียบกับผล closed-form
และรันชุดเทสต์ทั้งหมด (113 เทสต์)

### ตำแหน่งโค้ดที่เลือกโหมดและแปลงหน่วย

- **การเลือกโหมด:** หน้าเว็บส่งค่า `mode` มา `app.py` เรียก
  `validation.parse_mode()` ซึ่งปฏิเสธค่าที่ไม่รู้จัก จากนั้น
  `validation.MODE_FIELDS` เป็นตัวกำหนดว่าจะอ่านช่องใด แล้ว
  `evaluate._paths()` จับคู่โหมดกับคู่ `(solver, crosscheck)` ด้วย `if/elif`
  และโยน `ValueError` ถ้าไม่ตรงโหมดใดเลย ฝั่ง template ใช้ตัวเลือกแบบ
  `GET ?mode=` พร้อม `onchange="this.form.submit()"`, มี hidden field `mode`
  ในฟอร์ม POST และมีปุ่มสำรองใน `<noscript>`
- **การแปลงหน่วย:** `app.py` — `_selected_units()` อ่านช่อง `*_unit`,
  `_to_base_units()` คูณด้วย `UNIT_SCALE` (`Ω`/`kΩ`/`MΩ`, `V`/`mV`) โดยอาศัย
  `UNIT_CHOICES`/`DEFAULT_UNITS` และแปลงเฉพาะช่องที่โหมดนั้นใช้ ไม่มีการแปลง
  กลับในชั้นคำนวณ ส่วนการจัดรูปแบบเพื่อแสดงผลอยู่ที่ `engineering/format.py`

### Lab 04 — ส่วนที่ AI สร้างและสิ่งที่ตรวจ

AI สร้าง `spice_engine.py` (netlist, subprocess, parser), `spice_validation.py`,
`plotting.py`, route `/simulator` ใน `app.py`, template/CSS ของ Lab 04 และเทสต์
ที่เกี่ยวข้อง ผู้เขียนกำหนดเงื่อนไขว่าต้องรัน ngspice จริง ใช้โมเดล 2N3904,
แยกผล SPICE ออกจากผล analytical ของ Lab 03 และห้ามสร้างกราฟปลอม
ผู้เขียนตรวจ B1–B8 ในเบราว์เซอร์ เทียบค่าที่อ่านได้กับค่าคาดหมาย และบันทึก
หลักฐาน/ข้อจำกัดไว้ใน `docs/validation.md`

## ข้อจำกัด

หน้า Lab 03 ยังไม่มีงานวิเคราะห์ AC, อัตราขยาย, แบบจำลอง small-signal
หรือการจำลอง transient เช่นเดิม ส่วน Lab 04 รองรับวงจรอ้างอิง
voltage-divider common-emitter **หนึ่งวงจร** เท่านั้น ไม่มี schematic editor,
การนำเข้า netlist, วงจร arbitrary, FET, การวิเคราะห์ AC/transient ของโหมด
Fixed/Emitter, การกวาดอุณหภูมิ หรือ deployment

โมเดล 2N3904 เป็น model card มาตรฐาน ไม่ใช่ค่าที่วัดจากอุปกรณ์จริงในห้องแล็บ
ดังนั้นผล SPICE จึงต่างจาก Lab 03 analytical (`β = 100`, `VBE = 0.70 V`) ได้
และไม่ควรใช้แทนการวัดบน breadboard โดยตรง `VBE` ของ Lab 03 ยังเป็นค่าที่กรอก
เข้ามา ไม่ได้แก้จาก device model
