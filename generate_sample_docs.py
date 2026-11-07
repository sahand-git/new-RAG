"""
Generates realistic multi-page technical manuals for testing the Localized RAG app.
Creates:
1. Manual_P200_Robotics.pdf (5 pages)
2. Turbine_Generator_T900_Guide.pdf (5 pages)
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)
from reportlab.pdfgen import canvas

from src.config import DOCUMENTS_DIR


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages and prints running header & footer."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#4B5563"))

        # Header rule
        self.setStrokeColor(colors.HexColor("#D1D5DB"))
        self.setLineWidth(0.5)
        self.line(54, 745, 558, 745)
        self.drawString(54, 750, "OFFICIAL TECHNICAL MANUAL - SPECIFICATION & MAINTENANCE")

        # Footer rule
        self.line(54, 50, 558, 50)
        self.setFont("Helvetica", 9)
        self.drawString(54, 38, "CONFIDENTIAL & PROPRIETARY - LOCALIZED RAG REFERENCE")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 38, page_text)
        self.restoreState()


def create_p200_robotics_manual(output_path: Path):
    """Create 5-page P200 Robotics System technical manual."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
    )
    code_style = ParagraphStyle(
        "DocCode",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=11,
        fontName="Courier",
        textColor=colors.HexColor("#111827"),
    )

    story = []

    # ================= PAGE 1 =================
    story.append(Paragraph("System Manual: Apex P200 Industrial Articulated Robot", title_style))
    story.append(Paragraph("Document ID: DOC-P200-REV-4.2 | Issue Date: November 2025", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. System Overview & Core Specifications", h2_style))
    story.append(Paragraph(
        "The Apex P200 is a high-speed, 6-axis industrial articulated robot manipulator engineered for precision "
        "assembly, pick-and-place, and heavy-duty robotic welding. The mechanical arm incorporates absolute optical encoders "
        "on all six joints with battery-backed position retention during main supply interruptions.",
        body_style,
    ))

    specs_data = [
        ["Parameter", "Design Specification", "Tolerance / Unit"],
        ["Maximum Payload Capacity", "25.0 kg", "± 0.2 kg nominal"],
        ["Maximum Reach Envelope", "1,850 mm", "Spherical radial reach"],
        ["Pose Repeatability (ISO 9283)", "± 0.03 mm", "Tested at full extension"],
        ["Robot Weight (Mechanical)", "235 kg", "Excluding base pedestal"],
        ["Operating Voltage", "400 V AC ±10%", "3-Phase, 50/60 Hz"],
        ["Total Power Consumption", "4.2 kVA", "At continuous maximum duty"],
        ["Ambient Operating Temp", "0°C to +45°C", "Relative humidity 5% to 85%"],
        ["IP Ingress Protection", "IP67 Wrist / IP54 Body", "Standard factory configuration"],
    ]
    t1 = Table(specs_data, colWidths=[180, 160, 150])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F9FAFB"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t1)
    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("2. Safety Systems & Emergency Stop Architecture", title_style))
    story.append(Paragraph(
        "All P200 installations must comply with ISO 10218-1 and ANSI/RIA R15.06 industrial safety standards. "
        "The emergency stop safety loop is designed with a redundant dual-channel Category 4 / Performance Level e (PL e) architecture.",
        body_style,
    ))
    story.append(Paragraph("2.1 Emergency Stop Specifications & Trip Conditions", h2_style))
    story.append(Paragraph(
        "The primary E-Stop circuit utilizes safety contactors K1 and K2 wired to redundant terminal blocks TB1-12 and TB1-14. "
        "The total emergency stop response time from button actuation to zero mechanical movement must NOT exceed 25 milliseconds. "
        "Mechanical brakes engage automatically on all 6 axes within 15 milliseconds of power bus disconnection.",
        body_style,
    ))

    story.append(Paragraph("2.2 LiPo Backup Battery Replacement Protocol", h2_style))
    story.append(Paragraph(
        "The robot base pedestal houses a 3.6V lithium thionyl chloride (Li-SOCl2) backup battery pack (Part No. BAT-36-P200). "
        "This battery maintains absolute encoder calibration positions when main 400V power is switched off. "
        "CRITICAL REQUIREMENT: The battery pack must be replaced every 24 months or immediately when Warning LED D14 illuminates yellow. "
        "WARNING: Always replace the battery pack with MAIN POWER TURNED ON. If the battery is disconnected while main power is OFF, "
        "all joint encoder zero offsets will be permanently cleared from non-volatile memory, requiring a complete Axis Zero Calibration.",
        body_style,
    ))
    story.append(PageBreak())

    # ================= PAGE 3 =================
    story.append(Paragraph("3. Mechanical Calibration & Axis Zeroing", title_style))
    story.append(Paragraph(
        "Axis zero calibration aligns the mechanical kinematic model with internal optical encoder registers. "
        "Recalibration is mandatory following servo motor replacement, timing belt retensioning, or mechanical collision.",
        body_style,
    ))
    story.append(Paragraph("3.1 Mechanical Locking Pin Sequence", h2_style))
    story.append(Paragraph(
        "Step 1: Switch controller to MANUAL T1 mode (velocity capped at 250 mm/s).<br/>"
        "Step 2: Insert 8.0 mm ground calibration pin (Tool Part #CAL-PIN-08) into Axis 2 alignment borehole until fully seated.<br/>"
        "Step 3: Jog Axis 2 in joint coordinates until the pin slides freely through both the fixed link and the rotating casting.<br/>"
        "Step 4: Repeat the alignment sequence for Axis 3 using the 10.0 mm calibration pin (#CAL-PIN-10).<br/>"
        "Step 5: On the Teach Pendant, navigate to Menu -> Calibration -> Zero Calibration and confirm the offset write sequence.",
        body_style,
    ))

    story.append(Paragraph("3.2 Joint Range Limits & Maximum Speeds", h2_style))
    axis_data = [
        ["Joint Axis", "Motion Range", "Maximum Joint Speed", "Gearbox Type"],
        ["Axis 1 (Base Rotation)", "-170° to +170°", "180° / s", "RV Cycloidal Gearbox"],
        ["Axis 2 (Lower Arm)", "-100° to +135°", "150° / s", "RV Cycloidal Gearbox"],
        ["Axis 3 (Upper Arm)", "-210° to +65°", "180° / s", "RV Cycloidal Gearbox"],
        ["Axis 4 (Wrist Roll)", "-200° to +200°", "320° / s", "Harmonic Drive CSF-25"],
        ["Axis 5 (Wrist Pitch)", "-125° to +125°", "320° / s", "Harmonic Drive CSF-25"],
        ["Axis 6 (Wrist Twist)", "-360° to +360°", "460° / s", "Harmonic Drive CSF-20"],
    ]
    t2 = Table(axis_data, colWidths=[120, 110, 120, 140])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F3F4F6"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(t2)
    story.append(PageBreak())

    # ================= PAGE 4 =================
    story.append(Paragraph("4. Diagnostic Fault Codes & Troubleshooting Matrix", title_style))
    story.append(Paragraph(
        "When the robot controller detects an abnormal state, an alarm code appears on the Teach Pendant display. "
        "Refer to the table below for root causes and designated corrective actions.",
        body_style,
    ))

    fault_data = [
        ["Error Code", "Fault Description", "Root Cause", "Corrective Action"],
        ["Error E-301", "Over-current on Joint 3", "Mechanical binding or motor winding short", "Check Axis 3 gearbox backlash. Measure phase resistance (nominal 1.4 Ohms)."],
        ["Error E-405", "Resolver Comm Timeout", "Broken shielding on encoder cable harness", "Inspect flexible cable track bundle at Joint 2. Replace cable harness #CB-ENC-405."],
        ["Error E-512", "DC Bus Under-voltage", "Main supply dropped below 340V AC", "Verify facility 3-phase input supply with digital multimeter. Reset breaker Q1."],
        ["Error E-702", "Transformer Thermal Overload", "Cabinet internal temp exceeded 55°C", "Transformer thermal switch tripped at 115°C. Clean cabinet air filter and inspect fan B2."],
        ["Error E-819", "Collision Detection Trigger", "Torque feedback exceeded allowable envelope", "Check for physical obstacle in workspace. Clear obstruction and reset in Manual Mode."],
    ]
    t3 = Table(fault_data, colWidths=[80, 120, 140, 150])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#991B1B")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FEF2F2"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t3)
    story.append(PageBreak())

    # ================= PAGE 5 =================
    story.append(Paragraph("5. Preventive Maintenance & Lubrication Schedule", title_style))
    story.append(Paragraph(
        "Strict adherence to preventive maintenance intervals ensures kinematic accuracy and prevents unexpected downtime.",
        body_style,
    ))

    maint_data = [
        ["Operating Interval", "Inspection Item", "Lubricant / Part Spec", "Standard Criterion"],
        ["Every 500 Hours", "Mechanical brake holding torque", "N/A", "Brake must hold rated payload with 150% torque margin."],
        ["Every 2,500 Hours", "Axis 1-3 RV gear grease", "Kyodo Yushi VIGOGREASE RE0", "Extract 50 ml sample, inspect for metallic particulate contamination."],
        ["Every 5,000 Hours", "Axis 4-6 Harmonic drive grease", "Mobilith SHC 100 Synthetic", "Purge old grease through drain port until fresh grease appears."],
        ["Every 10,000 Hours", "Joint 4 timing belt tension", "Belt Spec: 450-5GT-15", "Measure natural frequency: 180 N tension (± 15 N). Replace if cracked."],
        ["Every 24 Months", "Encoder Memory Battery Pack", "BAT-36-P200 (Li-SOCl2)", "Mandatory replacement while controller is energized."],
    ]
    t4 = Table(maint_data, colWidths=[100, 130, 130, 130])
    t4.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065F46")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F0FDF4"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t4)
    story.append(Spacer(1, 15))
    story.append(Paragraph("5.1 Special Lubricant Handling Notice", h2_style))
    story.append(Paragraph(
        "CAUTION: Never mix VIGOGREASE RE0 with standard lithium complex petroleum greases. "
        "Incompatible chemical thickeners cause grease liquefaction and catastrophic tooth spalling inside the cycloidal reduction stages.",
        body_style,
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {output_path} (5 pages)")


def create_t900_turbine_guide(output_path: Path):
    """Create 5-page Turbine Generator T900 industrial guide."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#92400E"),
        spaceAfter=12,
    )
    h2_style = ParagraphStyle(
        "DocH2",
        parent=styles["Heading2"],
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1F2937"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#374151"),
        spaceAfter=6,
    )

    story = []

    # ================= PAGE 1 =================
    story.append(Paragraph("Technical Guide: Titan T900 Heavy Duty Gas Turbine", title_style))
    story.append(Paragraph("Manual Code: TG-T900-OM-2026 | Revision: 8.0", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("1. Turbine Baseline Thermodynamic Parameters", h2_style))
    story.append(Paragraph(
        "The Titan T900 is an industrial aeroderivative gas turbine designed for simple-cycle and combined-cycle "
        "power generation. The 17-stage axial-flow compressor operates with variable stator vanes (VSV) on the first four stages "
        "to prevent aerodynamic stall during cold startup conditions.",
        body_style,
    ))

    t_data = [
        ["Parameter", "ISO Baseline Value", "Operational Limit / Unit"],
        ["ISO Base Power Output", "45.0 MW", "At 15°C ambient, sea level"],
        ["Thermal Efficiency (Simple Cycle)", "38.5%", "Lower heating value basis"],
        ["Heat Rate (LHV)", "9,350 kJ / kWh", "± 1.5% tolerance"],
        ["Compressor Pressure Ratio", "21.5 : 1", "Nominal full-load pressure ratio"],
        ["Turbine Rotor Speed", "3,000 RPM (50Hz) / 3,600 RPM (60Hz)", "Driven via epicyclic reduction gearbox"],
        ["Exhaust Gas Mass Flow", "138.5 kg / s", "At base load rating"],
        ["Exhaust Gas Temperature", "540.0°C (1,004°F)", "Exhaust diffuser plenum exit"],
        ["NOx Emissions (Dry Low NOx)", "< 15 ppmvd", "Corrected to 15% O2 on natural gas"],
    ]
    t1 = Table(t_data, colWidths=[180, 160, 150])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#92400E")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFBEB"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t1)
    story.append(PageBreak())

    # ================= PAGE 2 =================
    story.append(Paragraph("2. Fuel Delivery & Conditioning Systems", title_style))
    story.append(Paragraph(
        "The T900 combustion system incorporates 14 dry low emission (DLE) combustor cans arranged in a can-annular configuration.",
        body_style,
    ))
    story.append(Paragraph("2.1 Fuel Gas Quality & Filtration Requirements", h2_style))
    story.append(Paragraph(
        "Natural gas supplied to the turbine skid must arrive at a regulated pressure of 28.0 to 32.0 bar gauge (barG). "
        "Gas temperature at the fuel control valve inlet must maintain a minimum of 20°C superheat above hydrocarbon and water dew points. "
        "The primary duplex fuel coalescing filters must provide 3.0 microns absolute filtration rating. "
        "Total sulfur content must not exceed 25 ppm weight.",
        body_style,
    ))
    story.append(Paragraph("2.2 Dual-Fuel Transfer Procedure", h2_style))
    story.append(Paragraph(
        "When transferring from fuel gas to backup distillate diesel (Ultra Low Sulfur Diesel, ASTM D975), the automated system "
        "opens the liquid purge valve and engages the high-pressure fuel pump at 45% load. "
        "Transfer duration must complete within 120 seconds to prevent thermal shock to the first-stage nozzle guide vanes.",
        body_style,
    ))
    story.append(PageBreak())

    # ================= PAGE 3 =================
    story.append(Paragraph("3. Lubrication Oil System & Bearing Temperatures", title_style))
    story.append(Paragraph(
        "The turbine lube oil skid provides pressurized lubrication and hydraulic control fluid to the journal bearings and reduction gearbox.",
        body_style,
    ))
    story.append(Paragraph("3.1 Lube Oil Specifications", h2_style))
    story.append(Paragraph(
        "The required lubricant is ISO VG 46 synthetic ester turbine oil conforming to GEK-32568 and MIL-PRF-23699 specifications. "
        "The main stainless steel oil reservoir has an active capacity of 4,500 liters. "
        "The normal lube oil supply temperature to the bearings must be maintained between 45.0°C and 50.0°C by the thermostatically controlled plate heat exchanger.",
        body_style,
    ))
    story.append(Paragraph("3.2 Bearing Temperature Trip Limits", h2_style))
    story.append(Paragraph(
        "Each hydrodynamic tilt-pad journal bearing is equipped with dual duplex PT100 RTDs embedded in the babbitt metal layer.<br/>"
        "- Normal Operating Temperature: 65°C to 75°C<br/>"
        "- High Temperature Alarm: 85.0°C<br/>"
        "- Emergency Turbine Trip Limit: 105.0°C<br/>"
        "If lube oil header pressure drops below 1.2 bar gauge, the DC emergency auxiliary pump engages within 0.8 seconds.",
        body_style,
    ))
    story.append(PageBreak())

    # ================= PAGE 4 =================
    story.append(Paragraph("4. Rotor Coupling Torquing & Mechanical Overhaul", title_style))
    story.append(Paragraph(
        "Precision mechanical assembly is critical during major inspection outages (hot gas path inspection every 24,000 equivalent operating hours).",
        body_style,
    ))
    story.append(Paragraph("4.1 Rotor Coupling Bolt Preload Specifications", h2_style))
    story.append(Paragraph(
        "The main rotor flange coupling connects the turbine shaft to the load gear pinion via 16 high-tensile nickel alloy bolts (M36 x 3.0, Grade 10.9). "
        "All bolts must be torqued using a calibrated hydraulic torque wrench in a diagonal criss-cross star sequence in three distinct stages:<br/>"
        "- Stage 1: Snug torque to 350 Nm<br/>"
        "- Stage 2: Intermediate torque to 800 Nm<br/>"
        "- Stage 3: Final certified torque to 1,450 Nm (± 25 Nm)<br/>"
        "CRITICAL: Apply MoS2 molybdenum disulfide anti-seize paste to threads and washer contact surfaces prior to torque sequence.",
        body_style,
    ))
    story.append(PageBreak())

    # ================= PAGE 5 =================
    story.append(Paragraph("5. Emergency Trip Setpoints & Safety Interlocks", title_style))
    story.append(Paragraph(
        "The safety management system (SMS) provides independent SIL 3 emergency trip logic across key physical parameters.",
        body_style,
    ))

    trip_data = [
        ["Monitored Parameter", "Sensor Instrument", "Warning Alarm Setpoint", "Emergency Trip Setpoint"],
        ["Rotor Radial Vibration", "Bently Nevada 3300 Proximity Probes", "4.5 mm / s RMS", "7.1 mm / s RMS (Instantaneous Trip)"],
        ["Turbine Shaft Overspeed", "Magnetic Speed Pickups (3 redundant)", "3,150 RPM (105%)", "3,300 RPM (110% of rated speed)"],
        ["Lube Oil Header Pressure", "Dual Differential Pressure Transmitters", "1.5 barG", "1.0 barG (Trip in 1.5 seconds)"],
        ["Exhaust Temperature Spread", "24 Chromel-Alumel Thermocouples", "Spread > 35°C", "Spread > 50°C (Combustor Flameout Trip)"],
        ["Compressor Inlet Differential Pressure", "Delta-P Manometer", "8.0 mbar", "12.0 mbar (Filter collapse warning)"],
    ]
    t5 = Table(trip_data, colWidths=[130, 130, 110, 120])
    t5.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#7F1D1D")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FEF2F2"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t5)
    story.append(Spacer(1, 15))
    story.append(Paragraph("5.1 Emergency Cooldown Barring Gear Cycle", h2_style))
    story.append(Paragraph(
        "Following any emergency trip from base load, the automatic hydraulic barring gear (turning gear) must rotate the shaft at "
        "45 RPM continuously for 48 hours. Turning prevents asymmetric thermal rotor sag (thermal bow), which can cause catastrophic blading rubbing.",
        body_style,
    ))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Generated: {output_path} (5 pages)")


def generate_all_samples():
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    p200_path = DOCUMENTS_DIR / "Manual_P200_Robotics.pdf"
    t900_path = DOCUMENTS_DIR / "Turbine_Generator_T900_Guide.pdf"

    print("Generating realistic technical manuals...")
    create_p200_robotics_manual(p200_path)
    create_t900_turbine_guide(t900_path)
    print("Done generating sample documents.")


if __name__ == "__main__":
    generate_all_samples()
