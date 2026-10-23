#!/usr/bin/env python3
"""
aviation_telemetry_engine.py
============================
Havacılık belgeselleri için otonom yayın kalitesinde (1080p Dark-Mode)
teknik telemetri, kokpit anomalisi ve taktiksel uçuş rotası grafik motoru.

Telif ve harici kütüphane bağımlılığı olmadan (yalnızca PIL/Pillow),
olayın türüne ve uçağın modeline göre 2 adet yüksek kaliteli infografik üretir:
  1. flight_trajectory_map.png  (Taktiksel Radar Rota Haritası & İrtifa Profili)
  2. flight_telemetry_gauge.png (Kokpit Gösterge Anomalisi / Sistem Arızası)
"""

import os
import math
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from typing import Optional, Dict, Any, List

W = 1920
H = 1080

# ── Font Yardımcısı ──
def get_font(size: int, bold: bool = False):
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Tarihi Kaza & Uçuş Bilgi Tabanı ──
INCIDENT_DATABASE = {
    "turkish_981": {
        "match_keys": ["turkish", "981", "ermenonville", "tc-jav", "orly", "ghendouer"],
        "flight_name": "Turkish Airlines Flight 981",
        "aircraft_type": "McDonnell Douglas DC-10-10",
        "aircraft_short": "DC-10",
        "departure_airport": "Paris Orly (ORY)",
        "destination_airport": "London Heathrow (LHR)",
        "climate": "NEUTRAL",
        "airline": "Turkish Airlines",
        "allowed_airlines": ["Turkish Airlines", "THY"],
        "prohibited_airlines": ["Swissair", "American Airlines", "United Airlines", "Scandinavian", "SAS", "Lufthansa", "Continental", "Delta", "Alitalia", "Air France", "KLM", "British Airways"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // TURKISH AIRLINES FLIGHT 981",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS DC-10-10   |   RADAR STATION: PARIS ORLY ATC (ORY)",
            "runway": "RUNWAY 08",
            "impact_point": "ERMENONVILLE FOREST (OISE)",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // DECOMPRESSION TO HIGH-SPEED DIVE",
            "alt_steps": [12000, 9000, 6000, 3000, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.22, 0.82), (0.40, 0.10), (0.55, 0.18), (0.75, 0.52), (0.95, 0.98)],
            "boxes": [
                ("CARGO DOOR BLOWOUT", "FL120 (12,000 FT)", (0, 200, 255)),
                ("TERMINAL DIVE SPEED", "430 KTS (800 KM/H)", (255, 60, 60)),
                ("PITCH-DOWN ATTITUDE", "-20° NOSE DOWN DIVE", (255, 200, 0)),
                ("FLIGHT CONTROLS", "TOTAL CABLE SEVERANCE", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // TURKISH AIRLINES FLIGHT 981",
            "subtitle": "SYSTEM: McDONNELL DOUGLAS DC-10 CARGO LATCH & CABIN FLOOR INTEGRITY",
            "left_label": "PILOT CABIN DIFFERENTIAL GAUGE",
            "left_value": "DELTA-P: 0.0 PSI (EXPLOSIVE LOSS)",
            "left_needle_angle": -60,
            "left_desc": "Outward pneumatic force blew cargo door free; passenger cabin floor buckled downward.",
            "right_label": "PRIMARY FLIGHT CONTROL HYDRAULICS",
            "right_value": "ELEVATOR / RUDDER: SEVERED",
            "right_needle_angle": -60,
            "right_desc": "SEVERED CONTROL CABLES & CRUSHED HYDRAULIC LINES - TOTAL LOSS OF PITCH CONTROL"
        },
        "wiki_clean_queries": ["Turkish Airlines DC-10", "THY DC-10", "TC-JAV", "Turkish Airlines DC-10-10"],
        "wiki_crash_queries": ["Turkish Airlines 981", "Ermenonville crash", "Turkish Airlines 981 wreckage", "DC-10 cargo door Windsor NTSB", "Ermenonville forest crash site 1974"]
    },
    "air_florida_90": {
        "match_keys": ["air florida", "potomac", "frozen sensors", "flight 90", "14th street"],
        "flight_name": "Air Florida Flight 90",
        "aircraft_type": "Boeing 737-222",
        "aircraft_short": "Boeing 737",
        "aircraft_category": "narrowbody_jet",
        "departure_airport": "Washington National (DCA)",
        "destination_airport": "Fort Lauderdale (FLL)",
        "climate": "WINTER",
        "airline": "Air Florida",
        "allowed_airlines": ["Air Florida"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "American Airlines", "Lufthansa", "SAS"],
        "prohibited_keywords": [
            "cessna", "c172", "piper", "single engine", "light aircraft", "beach", "summer", "palm trees",
            "night city", "neon", "skyline", "skyscraper", "museum", "hangar", "diagram", "slide"
        ],
        "atc_station": "WASHINGTON NATIONAL TOWER (DCA)",
        "investigating_agency": "NTSB (NATIONAL TRANSPORTATION SAFETY BOARD)",
        "probable_cause": "Failure to activate engine anti-ice causing iced PT2 pressure probes, false high EPR indications, and premature stall",
        "critical_factors": [
            ("ENGINE ANTI-ICE OFF", "Anti-ice left deactivated; snow blocked engine pressure ratio (PT2) sensors"),
            ("FALSE THRUST INDICATION", "Cockpit EPR showed 2.04 target power while actual thrust was only ~70%"),
            ("TAKEOFF STALL", "Severe pitch-up upon rotation due to leading-edge snow/ice contamination"),
            ("POTOMAC IMPACT", "Stalled at 352 ft, striking 14th St Bridge and plunging into frozen Potomac River")
        ],
        "cvr_dialogues": [
            ("Anti-ice is off. Airspeed alive, eighty knots.", "Slush on the runway... let's check the engine anti-ice."),
            ("Yes it is, there's eighty knots. Instruments look okay.", "Larry, that don't look right, does it?"),
            ("I know it! Pull up!", "Larry, we're going down, Larry...")
        ],
        "atc_dialogues": [
            "Palm 90, cleared for takeoff runway 36, no delay.",
            "Palm 90, contact Washington Departure on 118.3.",
            "Palm 90, Washington Tower, do you read? Radar contact lost!"
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // AIR FLORIDA FLIGHT 90",
            "subtitle": "AIRCRAFT: BOEING 737-222   |   RADAR STATION: WASHINGTON NATIONAL ATC (DCA)",
            "runway": "RUNWAY 36",
            "impact_point": "14th STREET BRIDGE / POTOMAC",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // ALTITUDE & VELOCITY DEFICIT",
            "alt_steps": [800, 600, 400, 200, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.20, 0.80), (0.50, 0.55), (0.65, 0.60), (0.80, 0.75), (0.95, 0.98)],
            "boxes": [
                ("INITIAL CLIMB SPEED", "144 KTS", (0, 200, 255)),
                ("MAX PEAK ALTITUDE", "352 FT", (255, 200, 0)),
                ("DESCENT / SINK RATE", "-1,850 FPM", (255, 60, 60)),
                ("CREW CONTROL STATUS", "STICK SHAKER ACTIVE", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // AIR FLORIDA FLIGHT 90",
            "subtitle": "SYSTEM: BOEING 737 PRATT & WHITNEY JT8D ENGINE SENSOR SUITE",
            "left_label": "PILOT INDICATED EPR (FALSE READING)",
            "left_value": "TARGET THRUST: 2.04 EPR",
            "left_needle_angle": 45,
            "left_desc": "Pilots set throttle levers based on this reading believing takeoff thrust was normal.",
            "right_label": "ACTUAL PHYSICAL THRUST (FATAL DEFICIT)",
            "right_value": "ACTUAL OUTPUT: 1.70 EPR (70%)",
            "right_needle_angle": -45,
            "right_desc": "CRITICAL THRUST DEFICIT - FROZEN PT2 PROBES BLOCKED BY ICE ACCUMULATION"
        },
        "wiki_clean_queries": ["Air Florida Boeing 737", "Air Florida 737", "N62AF"],
        "wiki_crash_queries": ["Air Florida 90 recovery", "Air Florida Flight 90 wreckage", "Potomac River 14th Street Bridge crash"]
    },
    "tenerife": {
        "match_keys": ["tenerife", "los rodeos", "pan am 1736", "klm 4805", "fog catastrophe"],
        "flight_name": "Tenerife Runway Collision",
        "aircraft_type": "Boeing 747-121 / Boeing 747-206B",
        "aircraft_short": "Boeing 747",
        "aircraft_category": "widebody_jet",
        "departure_airport": "Los Rodeos Airport (TFN)",
        "destination_airport": "Las Palmas (LPA)",
        "climate": "FOG",
        "airline": "KLM / Pan American",
        "allowed_airlines": ["KLM", "Pan Am", "Pan American"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Ryanair", "Emirates"],
        "prohibited_keywords": [
            "cessna", "c172", "single engine", "piper", "sunny", "blue sky",
            "night city", "neon", "skyline", "museum", "hangar", "diagram", "slide"
        ],
        "atc_station": "LOS RODEOS TOWER // TENERIFE ATC (TFN)",
        "investigating_agency": "CIAIAC / NTSB / DUTCH TRANSPORT SAFETY BOARD",
        "probable_cause": "KLM initiated takeoff roll without takeoff clearance in heavy fog while Pan Am was on runway",
        "critical_factors": [
            ("ZERO VISIBILITY FOG", "Dense fog rolled across Los Rodeos, dropping visibility below 300 meters"),
            ("NON-STANDARD PHRASEOLOGY", "Captain Van Zanten announced 'We are now at takeoff' without clearance"),
            ("RADIO HETERODYNE SQUAWK", "Simultaneous transmission blocked ATC's warning: 'Stand by for takeoff'"),
            ("RUNWAY COLLISION", "KLM 747 struck Pan Am 747 at 140 knots, destroying both aircraft")
        ],
        "cvr_dialogues": [
            ("Is Pan Am clear of the runway?", "He says he is clearing at taxiway three."),
            ("We gaan... We are now at takeoff.", "Wait, Papa Alpha did not clear! Did he clear?"),
            ("Look at that! Goddamn, he is coming!", "Get off! Get off! Off the runway!")
        ],
        "atc_dialogues": [
            "KLM 4805, report runway in sight. Backtrack runway 12.",
            "Pan Am 1736, report leaving the runway clear.",
            "KLM 4805, stand by for takeoff, I will call you... [heterodyne squawk]"
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // TENERIFE RUNWAY INCURSION",
            "subtitle": "AIRCRAFT: BOEING 747-206B & 747-121   |   RADAR STATION: LOS RODEOS ATC (TFN)",
            "runway": "RUNWAY 30 / 12",
            "impact_point": "RUNWAY INTERSECTION",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // RUNWAY ACCELERATION PROFILE",
            "alt_steps": [200, 150, 100, 50, 0],
            "alt_points_ratio": [(0.04, 0.98), (0.35, 0.98), (0.65, 0.98), (0.85, 0.88), (0.95, 0.98)],
            "boxes": [
                ("KLM TAKEOFF SPEED", "146 KTS (FULL POWER)", (0, 200, 255)),
                ("RUNWAY VISIBILITY", "< 300 METERS (FOG)", (255, 200, 0)),
                ("PAN AM POSITION", "INTERSECTING RUNWAY C-4", (255, 60, 60)),
                ("ATC TRANSMISSION", "HETERODYNE AUDIO SQUAWK", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // TENERIFE RUNWAY INCURSION",
            "subtitle": "SYSTEM: ATC RADIO CLEARANCE & DENSE FOG AUDIBLE DISRUPTION",
            "left_label": "KLM ENGINE THRUST LEVERS",
            "left_value": "EPR: 1.54 (TAKEOFF POWER)",
            "left_needle_angle": 45,
            "left_desc": "KLM Captain applied full takeoff thrust believing clearance was granted.",
            "right_label": "RUNWAY LINE OF SIGHT",
            "right_value": "VISIBILITY: ZERO / OBSCURED",
            "right_needle_angle": -50,
            "right_desc": "CRITICAL SQUAWK JAMMED ATC WARNING 'WE ARE STILL TAXIING ON THE RUNWAY'"
        },
        "wiki_clean_queries": ["KLM Boeing 747-206B", "Pan Am Boeing 747-121", "PH-BUF", "N736PA"],
        "wiki_crash_queries": ["Tenerife airport disaster", "Tenerife 1977 wreckage", "Los Rodeos runway collision 1977"]
    },
    "delta_191": {
        "match_keys": ["delta 191", "delta flight 191", "delta air lines 191", "n726da"],
        "flight_name": "Delta Air Lines Flight 191",
        "aircraft_type": "Lockheed L-1011 TriStar",
        "aircraft_short": "L-1011",
        "departure_airport": "DFW International Airport",
        "destination_airport": "Dallas/Fort Worth (DFW)",
        "climate": "STORMY",
        "airline": "Delta Air Lines",
        "allowed_airlines": ["Delta", "Delta Air Lines"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "American Airlines"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // DELTA FLIGHT 191",
            "subtitle": "AIRCRAFT: LOCKHEED L-1011-385-1   |   RADAR STATION: DFW APPROACH ATC",
            "runway": "RUNWAY 17L APPROACH",
            "impact_point": "HIGHWAY 114 / DFW PERIMETER",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // CONVECTIVE WINDSHEAR SINK RATE",
            "alt_steps": [2000, 1500, 1000, 500, 0],
            "alt_points_ratio": [(0.04, 0.15), (0.30, 0.35), (0.55, 0.50), (0.75, 0.70), (0.95, 0.98)],
            "boxes": [
                ("APPROACH AIRSPEED", "160 KTS", (0, 200, 255)),
                ("WINDSHEAR TAILWIND", "-54 KTS LOSS (SEVERE)", (255, 60, 60)),
                ("DESCENT SINK RATE", "-3,000 FPM DOWNDRAFT", (255, 200, 0)),
                ("ENGINE POWER SPOOL", "MAX TOGA THRUST LAG", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // DELTA FLIGHT 191",
            "subtitle": "SYSTEM: AIRSPEED INDICATOR VS MICROBURST DOWNDRAFT TAILWIND",
            "left_label": "INDICATED AIRSPEED (RAPID LOSS)",
            "left_value": "AIRSPEED: 115 KTS (STALL WARN)",
            "left_needle_angle": -45,
            "left_desc": "Sudden transition from strong headwind to severe tailwind triggered stall.",
            "right_label": "VERTICAL SPEED SINK RATE",
            "right_value": "DESCENT: -3,000 FPM",
            "right_needle_angle": -60,
            "right_desc": "SEVERE CONVECTIVE MICROBURST SINK RATE EXCEEDING MAXIMUM L-1011 CLIMB POWER"
        },
        "wiki_clean_queries": ["Delta Air Lines Lockheed L-1011", "Delta L-1011", "N726DA"],
        "wiki_crash_queries": ["Delta 191 crash", "Delta 191 wreckage", "Delta Flight 191 DFW"]
    },
    "usair_427": {
        "match_keys": ["usair 427", "usair flight 427", "rudder hard-over", "pittsburgh", "aliquippa"],
        "flight_name": "USAir Flight 427",
        "aircraft_type": "Boeing 737-3B7",
        "aircraft_short": "Boeing 737",
        "departure_airport": "Pittsburgh (PIT) Approach",
        "destination_airport": "Pittsburgh (PIT)",
        "climate": "NEUTRAL",
        "airline": "USAir",
        "allowed_airlines": ["USAir", "US Airways"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // USAIR FLIGHT 427",
            "subtitle": "AIRCRAFT: BOEING 737-3B7   |   RADAR STATION: PITTSBURGH APPROACH ATC",
            "runway": "RUNWAY 28R APPROACH",
            "impact_point": "ALIQUIPPA, PENNSYLVANIA",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // UNCOMMANDED RUDDER HARDOVER DIVE",
            "alt_steps": [8000, 6000, 4000, 2000, 0],
            "alt_points_ratio": [(0.04, 0.25), (0.25, 0.25), (0.50, 0.35), (0.75, 0.65), (0.95, 0.98)],
            "boxes": [
                ("ENTRY ALTITUDE", "6,000 FT MSL", (0, 200, 255)),
                ("UNCOMMANDED ROLL", "28° / SEC CONTINUOUS", (255, 60, 60)),
                ("DIVE AIRSPEED", "260+ KTS VERTICAL DIVE", (255, 200, 0)),
                ("RUDDER DEFLECTION", "FULL BLOWOVER JAM (LEFT)", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // USAIR FLIGHT 427",
            "subtitle": "SYSTEM: BOEING 737 RUDDER PCU DUAL SERVO VALVE REVERSAL",
            "left_label": "PILOT COMMANDED RUDDER INPUT",
            "left_value": "COMMAND: RIGHT RUDDER TRIM",
            "left_needle_angle": 50,
            "left_desc": "Pilot pressed right rudder pedal to counter wake turbulence roll.",
            "right_label": "ACTUAL PCU SERVO DEFLECTION",
            "right_value": "ACTUAL: FULL LEFT DEFLECTION",
            "right_needle_angle": -60,
            "right_desc": "THERMAL SHOCK SERVO VALVE JAM - RUDDER REVERSED TO OPPOSITE TRAVEL STOP"
        },
        "wiki_clean_queries": ["USAir Boeing 737-300", "USAir 737", "N513AU"],
        "wiki_crash_queries": ["USAir 427 crash", "USAir Flight 427 wreckage", "Aliquippa 737 crash"]
    },
    "valujet_592": {
        "match_keys": ["valujet", "valujet 592", "valujet flight 592", "n904vj"],
        "flight_name": "ValuJet Flight 592",
        "aircraft_type": "McDonnell Douglas DC-9-32",
        "aircraft_short": "DC-9",
        "departure_airport": "Miami International (MIA)",
        "destination_airport": "Atlanta (ATL)",
        "climate": "NEUTRAL",
        "airline": "ValuJet Airlines",
        "allowed_airlines": ["ValuJet"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // VALUJET FLIGHT 592",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS DC-9-32   |   RADAR STATION: MIAMI DEPARTURE ATC",
            "runway": "RUNWAY 09L",
            "impact_point": "FLORIDA EVERGLADES SWAMP",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // CARGO FIRE DESTRUCTION & DIVE",
            "alt_steps": [12000, 9000, 6000, 3000, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.25, 0.50), (0.45, 0.12), (0.65, 0.35), (0.95, 0.98)],
            "boxes": [
                ("FIRE DETECTED", "10,500 FT CLIMB", (0, 200, 255)),
                ("COCKPIT VISIBILITY", "ZERO (DENSE SMOKE)", (255, 60, 60)),
                ("DIVE DESCENT ANGLE", "-70° VERTICAL PLUNGE", (255, 200, 0)),
                ("IMPACT VELOCITY", "440 KTS INTO SWAMP", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // VALUJET FLIGHT 592",
            "subtitle": "SYSTEM: CLASS D CARGO HOLD CHEMICAL OXYGEN GENERATOR THERMAL RUNAWAY",
            "left_label": "CARGO BAY COMPARTMENT TEMP",
            "left_value": "TEMPERATURE: > 1,700°F (FIRE)",
            "left_needle_angle": 60,
            "left_desc": "Unexpended chemical oxygen canisters actuated, igniting cargo hold tires.",
            "right_label": "FLIGHT CONTROL CABLE INTEGRITY",
            "right_value": "CONTROLS: THERMAL FAILURE",
            "right_needle_angle": -60,
            "right_desc": "INTENSE HEAT SEVERED ELEVATOR CONTROL CABLES AND BURNED CABIN FLOOR"
        },
        "wiki_clean_queries": ["ValuJet DC-9", "ValuJet Airlines DC-9-32", "N904VJ"],
        "wiki_crash_queries": ["ValuJet 592 wreckage", "ValuJet 592 recovery Everglades", "ValuJet Flight 592 crash site"]
    },
    "swissair_111": {
        "match_keys": ["swissair 111", "swissair flight 111", "inferno in the ceiling", "md-11", "halifax", "peggy"],
        "flight_name": "Swissair Flight 111",
        "aircraft_type": "McDonnell Douglas MD-11",
        "aircraft_short": "MD-11",
        "departure_airport": "New York JFK (JFK)",
        "destination_airport": "Geneva (GVA)",
        "climate": "NEUTRAL",
        "airline": "Swissair",
        "allowed_airlines": ["Swissair"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // SWISSAIR FLIGHT 111",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS MD-11   |   RADAR STATION: HALIFAX ATC (YHZ)",
            "runway": "OCEANIC AIRSPACE",
            "impact_point": "PEGGY'S COVE, NOVA SCOTIA",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // IN-FLIGHT CEILING FIRE SPREAD",
            "alt_steps": [35000, 25000, 15000, 5000, 0],
            "alt_points_ratio": [(0.04, 0.05), (0.30, 0.05), (0.55, 0.45), (0.80, 0.75), (0.95, 0.98)],
            "boxes": [
                ("SMOKE REPORTED", "FL330 (33,000 FT)", (0, 200, 255)),
                ("COCKPIT DISPLAYS", "TOTAL SYSTEM BLACKOUT", (255, 60, 60)),
                ("GROSS WEIGHT", "240 TONS (FUEL DUMPING)", (255, 200, 0)),
                ("OCEAN IMPACT SPEED", "300 KTS HIGH-G DIVE", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // SWISSAIR FLIGHT 111",
            "subtitle": "SYSTEM: IN-FLIGHT ENTERTAINMENT (IFEN) METALLIZED MYLAR ARCING",
            "left_label": "CABIN ELECTRICAL BUS STATUS",
            "left_value": "BUS STATUS: ARMED NOMINAL",
            "left_needle_angle": 30,
            "left_desc": "Crew smelled smoke through air conditioning, initiating Swissair smoke checklist.",
            "right_label": "PRIMARY COCKPIT FLIGHT DISPLAYS",
            "right_value": "EFIS DISPLAYS: COMPLETE BLACKOUT",
            "right_needle_angle": -60,
            "right_desc": "FIRE SEVERED AVIONICS WIRING IN CEILING - ALL ELECTRONIC SCREENS FAILED"
        },
        "wiki_clean_queries": ["Swissair MD-11", "Swissair McDonnell Douglas MD-11", "HB-IWF"],
        "wiki_crash_queries": ["Swissair 111 wreckage", "Swissair Flight 111 memorial", "Swissair 111 Halifax recovery"]
    },
    "fedex_705": {
        "match_keys": ["fedex 705", "fedex flight 705", "aerobatics", "calloway", "memphis"],
        "flight_name": "FedEx Flight 705",
        "aircraft_type": "McDonnell Douglas DC-10-30",
        "aircraft_short": "DC-10",
        "departure_airport": "Memphis International (MEM)",
        "destination_airport": "San Jose (SJC)",
        "climate": "NEUTRAL",
        "airline": "Federal Express",
        "allowed_airlines": ["FedEx", "Federal Express"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // FEDEX FLIGHT 705",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS DC-10-30   |   RADAR STATION: MEMPHIS ATC",
            "runway": "RUNWAY 18R",
            "impact_point": "SAFE RETURN TO MEMPHIS",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // AEROBATIC ENVELOPE EXCEEDED",
            "alt_steps": [25000, 20000, 15000, 10000, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.25, 0.35), (0.50, 0.65), (0.75, 0.40), (0.95, 0.98)],
            "boxes": [
                ("MAXIMUM BANK ANGLE", "140° (INVERTED ROLL)", (255, 60, 60)),
                ("TRANSONIC DIVE SPEED", "460 KTS (PAST VNE)", (255, 60, 60)),
                ("PULL-OUT LOAD FACTOR", "+3.2 G MAXIMUM FORCE", (255, 200, 0)),
                ("FINAL RECOVERY STATUS", "SAFE TOUCHDOWN ON RWY 09", (0, 200, 255))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // FEDEX FLIGHT 705",
            "subtitle": "SYSTEM: DC-10 STRUCTURAL ENVELOPE EXTENSION TO SUBDUE HIJACKER",
            "left_label": "ATTITUDE HORIZON BANK ANGLE",
            "left_value": "BANK: 140° INVERTED ROLL",
            "left_needle_angle": 65,
            "left_desc": "First Officer Jim Tucker rolled wide-body DC-10 near inverted to throw attacker off-balance.",
            "right_label": "AIRSPEED INDICATOR VNE LIMIT",
            "right_value": "AIRSPEED: 460 KTS DIVE",
            "right_needle_angle": 55,
            "right_desc": "SUPERSONIC TRANSONIC FLUTTER - TRIPLE-JET EXCEEDED MAXIMUM STRUCTURAL LIMITS"
        },
        "wiki_clean_queries": ["FedEx DC-10", "FedEx McDonnell Douglas DC-10", "N306FE"],
        "wiki_crash_queries": ["FedEx 705 cockpit", "FedEx Flight 705 N306FE"]
    },
    "eastern_401": {
        "match_keys": ["eastern 401", "eastern air lines", "light bulb", "everglades", "l-1011"],
        "flight_name": "Eastern Air Lines Flight 401",
        "aircraft_type": "Lockheed L-1011-1 TriStar",
        "aircraft_short": "L-1011",
        "departure_airport": "Miami International (MIA)",
        "destination_airport": "Miami (MIA)",
        "climate": "NEUTRAL",
        "airline": "Eastern Air Lines",
        "allowed_airlines": ["Eastern", "Eastern Air Lines"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // EASTERN AIR LINES FLIGHT 401",
            "subtitle": "AIRCRAFT: LOCKHEED L-1011-1   |   RADAR STATION: MIAMI APPROACH ATC",
            "runway": "RUNWAY 9L APPROACH",
            "impact_point": "FLORIDA EVERGLADES (NIGHT)",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // UNDETECTED GRADUAL DESCENT",
            "alt_steps": [2500, 2000, 1500, 1000, 0],
            "alt_points_ratio": [(0.04, 0.20), (0.35, 0.20), (0.60, 0.40), (0.80, 0.70), (0.95, 0.98)],
            "boxes": [
                ("ASSIGNED ALTITUDE", "2,000 FT HOLDING", (0, 200, 255)),
                ("UNNOTICED SINK RATE", "-200 FPM GRADUAL", (255, 200, 0)),
                ("NOSE GEAR LIGHT BULB", "BURNT FILAMENT ($12)", (255, 60, 60)),
                ("IMPACT VELOCITY", "227 MPH INTO EVERGLADES", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // EASTERN AIR LINES FLIGHT 401",
            "subtitle": "SYSTEM: LOCKHEED L-1011 AUTOPILOT ALTITUDE HOLD DISENGAGEMENT",
            "left_label": "AUTOPILOT ALTITUDE HOLD STATUS",
            "left_value": "ALT HOLD: DISCONNECTED (BUMP)",
            "left_needle_angle": -40,
            "left_desc": "Accidental yoke bump disengaged altitude hold while crew focused on gear light.",
            "right_label": "RADIO ALTIMETER READOUT",
            "right_value": "ALTITUDE: 100 FT (PULL UP!)",
            "right_needle_angle": -60,
            "right_desc": "CFIT INTO EVERGLADES AT 227 MPH WHILE CREW ATTEMPTED TO REPLACE LIGHT BULB"
        },
        "wiki_clean_queries": ["Eastern Air Lines Lockheed L-1011", "Eastern L-1011", "N310EA"],
        "wiki_crash_queries": ["Eastern 401 wreckage Everglades", "Eastern Air Lines 401 crash site", "Eastern 401 recovery"]
    },
    "aeroflot_593": {
        "match_keys": ["aeroflot 593", "aeroflot flight 593", "child at the controls", "kudrinsky", "mezhdurechensk"],
        "flight_name": "Aeroflot Flight 593",
        "aircraft_type": "Airbus A310-304",
        "aircraft_short": "A310",
        "departure_airport": "Moscow Sheremetyevo (SVO)",
        "destination_airport": "Hong Kong (HKG)",
        "climate": "WINTER",
        "airline": "Aeroflot",
        "allowed_airlines": ["Aeroflot"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // AEROFLOT FLIGHT 593",
            "subtitle": "AIRCRAFT: AIRBUS A310-304   |   RADAR STATION: NOVOSIBIRSK EN ROUTE",
            "runway": "FL330 CRUISE",
            "impact_point": "KUZNETSK ALATAU, SIBERIA",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // PARTIAL AUTOPILOT OVERRIDE SPIRAL",
            "alt_steps": [35000, 25000, 15000, 5000, 0],
            "alt_points_ratio": [(0.04, 0.05), (0.35, 0.05), (0.55, 0.35), (0.75, 0.65), (0.95, 0.98)],
            "boxes": [
                ("CRUISE ALTITUDE", "FL330 (33,000 FT)", (0, 200, 255)),
                ("AUTOPILOT ROLL STATUS", "SILENT OVERRIDE (CHILD)", (255, 60, 60)),
                ("MAXIMUM BANK ANGLE", "75° SPIRAL DIVE", (255, 200, 0)),
                ("IMPACT TERRAIN", "SIBERIAN TAIGA MOUNTAIN", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // AEROFLOT FLIGHT 593",
            "subtitle": "SYSTEM: AIRBUS A310 AUTOPILOT PARTIAL TORQUE OVERRIDE",
            "left_label": "AUTOPILOT ROLL CHANNEL STATUS",
            "left_value": "ROLL: DISENGAGED (SILENT)",
            "left_needle_angle": -45,
            "left_desc": "Child's pressure on control wheel disconnected roll servos without audible chime.",
            "right_label": "ATTITUDE HORIZON / ROLL RATE",
            "right_value": "BANK ANGLE: 75° SPIRAL DIVE",
            "right_needle_angle": 60,
            "right_desc": "EXTREME BANK CREATED HIGH-G SPIRAL DIVE PINNING PILOTS INTO THEIR SEATS"
        },
        "wiki_clean_queries": ["Aeroflot Airbus A310", "Aeroflot A310", "F-OGQS"],
        "wiki_crash_queries": ["Aeroflot 593 crash site", "Aeroflot 593 wreckage Siberia", "Aeroflot Flight 593 memorial"]
    },
    "gol_1907": {
        "match_keys": ["gol 1907", "gol transportes", "legacy 600", "pr-gtd", "n600xl"],
        "flight_name": "Gol Flight 1907 / Embraer Legacy 600",
        "aircraft_type": "Boeing 737-8EH / Embraer Legacy 600",
        "aircraft_short": "Boeing 737",
        "departure_airport": "Manaus Eduardo Gomes (MAO)",
        "destination_airport": "Brasilia (BSB)",
        "climate": "NEUTRAL",
        "airline": "Gol Transportes Aéreos",
        "allowed_airlines": ["Gol", "Gol Transportes Aéreos"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // GOL 1907 MID-AIR COLLISION",
            "subtitle": "AIRCRAFT: BOEING 737-8EH & EMBRAER LEGACY   |   RADAR STATION: CINDACTA I",
            "runway": "FL370 AIRWAY UZ44",
            "impact_point": "MATO GROSSO AMAZON RAINFOREST",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // MID-AIR WINGTIP IMPACT & DIVE",
            "alt_steps": [40000, 30000, 20000, 10000, 0],
            "alt_points_ratio": [(0.04, 0.08), (0.40, 0.08), (0.60, 0.35), (0.80, 0.70), (0.95, 0.98)],
            "boxes": [
                ("COLLISION ALTITUDE", "FL370 (37,000 FT)", (0, 200, 255)),
                ("LEGACY TRANSPONDER", "STANDBY (TCAS INACTIVE)", (255, 60, 60)),
                ("737 WING SEVERANCE", "LEFT WINGLET & 30 FT SPAR", (255, 200, 0)),
                ("TERRAIN IMPACT", "AMAZON DENSE JUNGLE", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // GOL 1907 & LEGACY 600",
            "subtitle": "SYSTEM: TCAS (TRAFFIC COLLISION AVOIDANCE) TRANSPONDER SILENCE",
            "left_label": "LEGACY 600 XPDR TRANSPONDER",
            "left_value": "TRANSPONDER: STANDBY (OFF)",
            "left_needle_angle": -50,
            "left_desc": "Pilot's footrest contact accidentally deactivated transponder TCAS squawk.",
            "right_label": "GOL 737 TCAS TRAFFIC DISPLAY",
            "right_value": "TCAS WARNING: NO TARGET VISIBLE",
            "right_needle_angle": -50,
            "right_desc": "MID-AIR WINGTIP SLICE IN AMAZON JUNGLE - TOTAL STRUCTURAL BREAKUP OF 737"
        },
        "wiki_clean_queries": ["Gol Boeing 737-800", "PR-GTD", "Embraer Legacy 600 N600XL"],
        "wiki_crash_queries": ["Gol 1907 wreckage Amazon", "Gol Flight 1907 crash site Mato Grosso", "PR-GTD wreckage"]
    },
    "tuninter_1153": {
        "match_keys": ["tuninter 1153", "tuninter flight 1153", "wrong gauge", "atr 72", "sicily", "bari"],
        "flight_name": "Tuninter Flight 1153",
        "aircraft_type": "ATR 72-202",
        "aircraft_short": "ATR 72",
        "aircraft_category": "turboprop",
        "departure_airport": "Bari Karol Wojtyla (BRI)",
        "destination_airport": "Djerba (DJE)",
        "climate": "TROPICAL",
        "airline": "Tuninter",
        "allowed_airlines": ["Tuninter"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Qatar Airways", "Qatar", "Emirates", "Air France", "Lufthansa", "British Airways", "Alitalia"],
        "prohibited_aircraft": ["Boeing", "Airbus", "jet", "turbofan", "winglet", "C-45", "Model 18", "T-29", "DC-3"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // TUNINTER FLIGHT 1153",
            "subtitle": "AIRCRAFT: ATR 72-202   |   RADAR STATION: PALERMO ATC (PMO)",
            "runway": "RUNWAY 07",
            "impact_point": "18 MILES OFF PALERMO, SICILY",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // DUAL ENGINE FUEL EXHAUSTION GLIDE",
            "alt_steps": [20000, 15000, 10000, 5000, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.25, 0.15), (0.50, 0.15), (0.75, 0.55), (0.95, 0.98)],
            "boxes": [
                ("CRUISE ALTITUDE", "FL170 (17,000 FT)", (0, 200, 255)),
                ("DUAL FLAMEOUT", "BOTH ENGINES OUT", (255, 60, 60)),
                ("INDICATED FUEL", "2,700 KG (FALSE GAUGE)", (255, 200, 0)),
                ("ACTUAL FUEL", "0 KG (TOTAL EXHAUSTION)", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // TUNINTER FLIGHT 1153",
            "subtitle": "SYSTEM: FUEL QUANTITY INDICATOR (FQI) INCOMPATIBILITY",
            "left_label": "COCKPIT FQI (ATR 42 GAUGE INSTALLED)",
            "left_value": "FUEL: 2,700 KG (SUFFICIENT)",
            "left_needle_angle": 45,
            "left_desc": "Mechanics erroneously installed ATR 42 fuel gauge into wider ATR 72 tanks.",
            "right_label": "ACTUAL PHYSICAL FUEL REMAINING",
            "right_value": "ACTUAL: 0 KG (EMPTY TANKS)",
            "right_needle_angle": -60,
            "right_desc": "DUAL ENGINE FLAMEOUT OVER MEDITERRANEAN - FORCED WATER DITCHING OFF SICILY"
        },
        "wiki_clean_queries": ["Tuninter ATR 72", "TS-LBB", "ATR 72 Tuninter"],
        "wiki_crash_queries": ["Tuninter 1153 ditching Sicily", "TS-LBB salvage", "Tuninter 1153 rescue", "Tuninter 1153 wreckage Italian Coast Guard"]
    },
    "flash_604": {
        "match_keys": ["flash airlines 604", "flash 604", "sharm el sheikh", "red sea"],
        "flight_name": "Flash Airlines Flight 604",
        "aircraft_type": "Boeing 737-3Q8",
        "aircraft_short": "Boeing 737-300",
        "aircraft_category": "narrowbody_jet",
        "departure_airport": "Sharm El Sheikh (SSH)",
        "destination_airport": "Cairo (CAI)",
        "climate": "NIGHT",
        "airline": "Flash Airlines",
        "allowed_airlines": ["Flash Airlines"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Qatar Airways", "Qatar", "Emirates", "EgyptAir", "Buzz", "Ryanair"],
        "prohibited_aircraft": ["737 MAX", "737-MAX", "737-800", "737-200", "glass cockpit", "touchscreen", "C-45", "Model 18", "T-29", "turboprop", "propeller"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // FLASH AIRLINES FLIGHT 604",
            "subtitle": "AIRCRAFT: BOEING 737-3Q8   |   RADAR STATION: SHARM EL SHEIKH ATC",
            "runway": "RUNWAY 22R",
            "impact_point": "RED SEA (GULF OF AQABA)",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // SPATIAL DISORIENTATION NIGHT DIVE",
            "alt_steps": [6000, 4500, 3000, 1500, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.35, 0.10), (0.60, 0.20), (0.80, 0.60), (0.95, 0.98)],
            "boxes": [
                ("INITIAL CLIMB OUT", "5,460 FT PEAK", (0, 200, 255)),
                ("UNCOMMANDED ROLL", "111° OVERBANK (RIGHT)", (255, 60, 60)),
                ("PITCH ANGLE DIVE", "-24° NOSE DOWN", (255, 200, 0)),
                ("IMPACT AIRSPEED", "416 KTS INTO RED SEA", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // FLASH AIRLINES FLIGHT 604",
            "subtitle": "SYSTEM: SPATIAL DISORIENTATION & AUTO-THROTTLE DISCONNECT",
            "left_label": "ATTITUDE HORIZON BANK ANGLE",
            "left_value": "BANK: 111° STEEP RIGHT",
            "left_needle_angle": 60,
            "left_desc": "Spatial disorientation over pitch-black sea caused crew to miss severe roll.",
            "right_label": "BAROMETRIC ALTIMETER SINK RATE",
            "right_value": "SINK RATE: -10,000 FPM",
            "right_needle_angle": -60,
            "right_desc": "CATASTROPHIC NIGHT WATER IMPACT IN GULF OF AQABA SECONDS AFTER OVERBANK"
        },
        "wiki_clean_queries": ["Flash Airlines Boeing 737", "SU-ZCF", "Boeing 737-300 Flash Airlines"],
        "wiki_crash_queries": ["Flash Airlines 604 salvage French Navy", "Flash Airlines 604 Red Sea", "SU-ZCF recovery", "Flash Airlines 604 memorial", "Flash Airlines 604 BEA"]
    },
    "air_midwest_5481": {
        "match_keys": ["air midwest 5481", "midwest 5481", "charlotte", "beechcraft"],
        "flight_name": "Air Midwest Flight 5481",
        "aircraft_type": "Beechcraft 1900D",
        "aircraft_short": "Beechcraft 1900D",
        "aircraft_category": "turboprop",
        "departure_airport": "Charlotte Douglas (CLT)",
        "destination_airport": "Greenville-Spartanburg (GSP)",
        "climate": "NEUTRAL",
        "airline": "Air Midwest",
        "allowed_airlines": ["Air Midwest", "US Airways Express"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Qatar Airways", "Qatar", "Emirates", "Colgan", "Colgan Air", "N240CJ"],
        "prohibited_aircraft": ["Boeing", "Airbus", "jet", "turbofan", "winglet", "C-45", "Model 18", "T-29", "Everest", "Himalaya", "Marília Mendonça", "King Air", "Model 17"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // AIR MIDWEST FLIGHT 5481",
            "subtitle": "AIRCRAFT: BEECHCRAFT 1900D   |   RADAR STATION: CHARLOTTE TOWER ATC",
            "runway": "RUNWAY 18R",
            "impact_point": "US AIRWAYS MAINTENANCE HANGAR",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // ELEVATOR MISRIGGING STALL",
            "alt_steps": [1500, 1200, 900, 600, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.30, 0.50), (0.55, 0.20), (0.75, 0.50), (0.95, 0.98)],
            "boxes": [
                ("TAKEOFF SPEED", "102 KTS ROTATION", (0, 200, 255)),
                ("PITCH-UP ATTITUDE", "+54° NOSE HIGH STALL", (255, 60, 60)),
                ("PEAK ALTITUDE", "1,150 FT AGL", (255, 200, 0)),
                ("ELEVATOR TRAVEL", "ONLY 7° NOSE-DOWN (RIG ERR)", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // AIR MIDWEST FLIGHT 5481",
            "subtitle": "SYSTEM: ELEVATOR CONTROL CABLE MISRIGGING & AFT CG",
            "left_label": "PILOT COMMANDED NOSE-DOWN PUSH",
            "left_value": "YOKE: FULL FORWARD PUSH",
            "left_needle_angle": -50,
            "left_desc": "Pilot shoved control column completely forward to stop catastrophic pitch-up.",
            "right_label": "ACTUAL ELEVATOR SURFACE DEFLECTION",
            "right_value": "ELEVATOR: RESTRICTED TO -7°",
            "right_needle_angle": -25,
            "right_desc": "MAINTENANCE RIGGING ERROR REDUCED NOSE-DOWN TRAVEL BY 50% - UNRECOVERABLE STALL"
        },
        "wiki_clean_queries": ["Air Midwest Beechcraft 1900D", "N233YV", "Beechcraft 1900D US Airways Express"],
        "wiki_crash_queries": ["Air Midwest 5481 wreckage", "Air Midwest Flight 5481 crash hangar CLT", "Air Midwest 5481 NTSB investigation", "Air Midwest 5481 N233YV", "N233YV wreckage"]
    },
    "austral_2553": {
        "match_keys": ["austral 2553", "austral flight 2553", "frozen pitot", "fray bentos", "uruguay"],
        "flight_name": "Austral Líneas Aéreas Flight 2553",
        "aircraft_type": "McDonnell Douglas DC-9-32",
        "aircraft_short": "DC-9",
        "departure_airport": "Posadas (PSS)",
        "destination_airport": "Buenos Aires (AEP)",
        "climate": "NEUTRAL",
        "airline": "Austral Líneas Aéreas",
        "allowed_airlines": ["Austral", "Austral Líneas Aéreas"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // AUSTRAL FLIGHT 2553",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS DC-9-32   |   RADAR STATION: EZEIZA CONTROL",
            "runway": "FL350 EN ROUTE",
            "impact_point": "FRAY BENTOS, URUGUAY",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // PITOT ICING & TRANSONIC DIVE",
            "alt_steps": [35000, 25000, 15000, 5000, 0],
            "alt_points_ratio": [(0.04, 0.05), (0.35, 0.05), (0.55, 0.35), (0.75, 0.70), (0.95, 0.98)],
            "boxes": [
                ("CRUISING ALTITUDE", "FL350 (35,000 FT)", (0, 200, 255)),
                ("FALSE AIRSPEED READOUT", "DROPPED TO 160 KTS", (255, 60, 60)),
                ("ACTUAL DIVE SPEED", "MACH 0.88 (> VNE LIMIT)", (255, 200, 0)),
                ("SLAT EXTENSION SPEED", "DEPLOYED AT 450+ KTS", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // AUSTRAL FLIGHT 2553",
            "subtitle": "SYSTEM: PITOT TUBE HEATER FAILURE & FALSE AIRSPEED INDICATION",
            "left_label": "PILOT INDICATED AIRSPEED (FALSE)",
            "left_value": "INDICATED: 150 KTS (STALL ALARM)",
            "left_needle_angle": -50,
            "left_desc": "Frozen pitot tube caused airspeed indicator to read dangerously low.",
            "right_label": "ACTUAL TRUE PHYSICAL AIRSPEED",
            "right_value": "TRUE AIRSPEED: > 500 KTS (DIVE)",
            "right_needle_angle": 60,
            "right_desc": "PILOTS EXTENDED SLATS AT TRANSONIC SPEED - STRUCTURAL OVERLOAD AND BREAKUP"
        },
        "wiki_clean_queries": ["Austral DC-9", "Austral Líneas Aéreas DC-9-32", "LV-WEG"],
        "wiki_crash_queries": ["Austral 2553 wreckage Fray Bentos", "Austral Flight 2553 crash crater Uruguay"]
    },
    "aa_587": {
        "match_keys": ["american airlines 587", "aa 587", "aa flight 587", "belle harbor", "rudder reversals"],
        "flight_name": "American Airlines Flight 587",
        "aircraft_type": "Airbus A300B4-605R",
        "aircraft_short": "A300",
        "aircraft_category": "widebody_jet",
        "departure_airport": "New York JFK (JFK)",
        "destination_airport": "Santo Domingo (SDQ)",
        "climate": "NEUTRAL",
        "airline": "American Airlines",
        "allowed_airlines": ["American Airlines", "American"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Qatar Airways", "Qatar", "Emirates", "Air France", "Lufthansa", "British Airways"],
        "prohibited_aircraft": ["Boeing", "turboprop", "propeller", "C-45", "Model 18", "T-29", "Piper", "Cessna", "scale model", "plastic model"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // AMERICAN AIRLINES FLIGHT 587",
            "subtitle": "AIRCRAFT: AIRBUS A300B4-605R   |   RADAR STATION: NEW YORK TRACON",
            "runway": "RUNWAY 31L",
            "impact_point": "BELLE HARBOR, QUEENS, NEW YORK",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // WAKE TURBULENCE & TAIL DETACHMENT",
            "alt_steps": [3000, 2400, 1800, 1200, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.35, 0.20), (0.55, 0.15), (0.75, 0.50), (0.95, 0.98)],
            "boxes": [
                ("WAKE ENCOUNTER", "2,500 FT CLIMB", (0, 200, 255)),
                ("RUDDER PEDAL CYCLES", "5 CYCLIC REVERSALS", (255, 60, 60)),
                ("AERODYNAMIC SIDE LOAD", "+0.4 G LATERAL FORCE", (255, 200, 0)),
                ("VERTICAL STABILIZER", "COMPLETE TAIL DETACHMENT", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // AMERICAN AIRLINES FLIGHT 587",
            "subtitle": "SYSTEM: AIRBUS A300 RUDDER SYSTEM SENSITIVITY & TAIL FIN INTEGRITY",
            "left_label": "PILOT RUDDER PEDAL INPUT",
            "left_value": "PEDAL: RAPID ALTERNATING TRAVEL",
            "left_needle_angle": 55,
            "left_desc": "First Officer repeatedly commanded aggressive full-left and full-right rudder.",
            "right_label": "COMPOSITE FIN ATTACHMENT LUGS",
            "right_value": "STRESS: 200% BEYOND DESIGN LIMIT",
            "right_needle_angle": 65,
            "right_desc": "AERODYNAMIC LOADS RIPPED VERTICAL STABILIZER FROM FUSELAGE IN MID-AIR"
        },
        "wiki_clean_queries": ["American Airlines Airbus A300", "American Airlines A300", "N14053"],
        "wiki_crash_queries": [
            "Flight 587 vertical stabilizer Jamaica Bay",
            "AA 587 wreckage Belle Harbor",
            "Flight 587 memorial Queens",
            "American Airlines 587 NTSB investigation",
            "N14053 crash site Queens"
        ]
    },
    "sq_006": {
        "match_keys": ["singapore airlines 006", "sq 006", "sq flight 006", "singapore 006", "9v-spk", "chiang kai-shek"],
        "flight_name": "Singapore Airlines Flight 006",
        "aircraft_type": "Boeing 747-412",
        "aircraft_short": "Boeing 747-400",
        "aircraft_category": "widebody_jet",
        "departure_airport": "Taipei Chiang Kai-shek (TPE)",
        "destination_airport": "Los Angeles (LAX)",
        "climate": "STORMY",
        "airline": "Singapore Airlines",
        "allowed_airlines": ["Singapore Airlines"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Martinair", "Martinair Cargo", "KLM", "China Airlines", "EVA Air", "Emirates", "Qatar Airways", "Qatar"],
        "prohibited_aircraft": ["C-45", "Model 18", "T-29", "turboprop", "propeller", "Cessna", "Piper"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // SINGAPORE AIRLINES FLIGHT 006",
            "subtitle": "AIRCRAFT: BOEING 747-412   |   RADAR STATION: TAIPEI TOWER ATC",
            "runway": "RUNWAY 05R (CLOSED FOR REPAIR)",
            "impact_point": "RUNWAY 05R CONSTRUCTION SITE",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // CLOSED RUNWAY COLLISION ROLL",
            "alt_steps": [200, 150, 100, 50, 0],
            "alt_points_ratio": [(0.04, 0.98), (0.40, 0.98), (0.70, 0.98), (0.88, 0.92), (0.95, 0.98)],
            "boxes": [
                ("TAKEOFF GROUND SPEED", "140 KTS ACCELERATION", (0, 200, 255)),
                ("WEATHER CONDITIONS", "TYPHOON XANGSANE RAIN", (255, 60, 60)),
                ("RUNWAY OBSTACLES", "CONCRETE BARRIERS & CRANES", (255, 200, 0)),
                ("AIRFRAME INTEGRITY", "TORN IN TWO BY EXCAVATOR", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // SINGAPORE AIRLINES FLIGHT 006",
            "subtitle": "SYSTEM: PARA-VISUAL DISPLAY (PVD) & TAXIWAY RUNWAY HEADING ALIGNMENT",
            "left_label": "COCKPIT PVD (RUNWAY GUIDANCE)",
            "left_value": "PVD: UNLOCKED / NO SIGNAL",
            "left_needle_angle": -45,
            "left_desc": "Crew lined up on unlit closed runway 05R without PVD localizer lock.",
            "right_label": "RUNWAY 05R PHYSICAL STATUS",
            "right_value": "STATUS: ACTIVE CONSTRUCTION ZONE",
            "right_needle_angle": 60,
            "right_desc": "TAKEOFF ROLL INTO HEAVY EXCAVATION EQUIPMENT AT 150 KTS DURING TYPHOON"
        },
        "wiki_clean_queries": ["Singapore Airlines Boeing 747-400", "9V-SPK", "Singapore Airlines 747-412"],
        "wiki_crash_queries": ["Singapore Airlines 006 wreckage", "SQ006 crash site Taipei", "Singapore Airlines Flight 006 9V-SPK", "Singapore Airlines 006 runway 05R", "SQ006 excavator wreckage"]
    },
    "lauda_004": {
        "match_keys": ["lauda air flight 004", "lauda flight 004", "lauda air 004", "lauda 004", "lauda", "oe-lav", "suphan buri"],
        "flight_name": "Lauda Air Flight 004",
        "aircraft_type": "Boeing 767-3Z9ER",
        "aircraft_short": "Boeing 767",
        "departure_airport": "Bangkok Don Mueang (BKK)",
        "destination_airport": "Vienna (VIE)",
        "climate": "TROPICAL",
        "airline": "Lauda Air",
        "allowed_airlines": ["Lauda Air"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // LAUDA AIR FLIGHT 004",
            "subtitle": "AIRCRAFT: BOEING 767-3Z9ER   |   RADAR STATION: BANGKOK EN ROUTE",
            "runway": "FL320 CRUISE",
            "impact_point": "DAN CHANG / SUPHAN BURI, THAILAND",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // IN-FLIGHT THRUST REVERSAL DIVE",
            "alt_steps": [35000, 28000, 21000, 14000, 0],
            "alt_points_ratio": [(0.04, 0.08), (0.35, 0.08), (0.55, 0.35), (0.75, 0.70), (0.95, 0.98)],
            "boxes": [
                ("CRUISE ALTITUDE", "FL320 (32,000 FT)", (0, 200, 255)),
                ("REVERSER DEPLOYMENT", "NO. 1 LEFT ENGINE (REV)", (255, 60, 60)),
                ("DIVE VELOCITY", "MACH 0.99 BREAKUP", (255, 200, 0)),
                ("TIME TO BREAKUP", "ONLY 29 SECONDS", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // LAUDA AIR FLIGHT 004",
            "subtitle": "SYSTEM: PRATT & WHITNEY PW4000 THRUST REVERSER HYDRAULIC VALVE",
            "left_label": "REV ISOLATION VALVE COCKPIT LIGHT",
            "left_value": "STATUS: ADVISORY WARNING FLASH",
            "left_needle_angle": 35,
            "left_desc": "Captains believed warning was intermittent sensor glitch, citing manual.",
            "right_label": "LEFT ENGINE PHYSICAL REVERSER",
            "right_value": "PHYSICAL: FULL IN-FLIGHT DEPLOY",
            "right_needle_angle": 60,
            "right_desc": "UNCOMMANDED DEPLOYMENT DESTROYED WING LIFT - AIRFRAME BROKE UP AT MACH 0.99"
        },
        "wiki_clean_queries": ["Lauda Air Boeing 767", "OE-LAV", "Lauda Air 767-300ER"],
        "wiki_crash_queries": ["Lauda Air 004 wreckage Thailand", "OE-LAV crash site", "Lauda Air Flight 004 memorial"]
    },
    "united_232": {
        "match_keys": ["united 232", "united airlines 232", "sioux city", "al haynes"],
        "flight_name": "United Airlines Flight 232",
        "aircraft_type": "McDonnell Douglas DC-10-10",
        "aircraft_short": "DC-10",
        "departure_airport": "Denver / Sioux City (SUX)",
        "destination_airport": "Chicago O'Hare (ORD)",
        "climate": "NEUTRAL",
        "airline": "United Airlines",
        "allowed_airlines": ["United Airlines", "United"],
        "prohibited_airlines": ["Turkish Airlines", "Delta", "American Airlines"],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // UNITED AIRLINES FLIGHT 232",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS DC-10-10   |   RADAR STATION: SIOUX CITY ATC (SUX)",
            "runway": "RUNWAY 22 CRASH LANDING",
            "impact_point": "SIOUX GATEWAY AIRPORT",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // TRIPLE HYDRAULIC LOSS DESCENT",
            "alt_steps": [37000, 25000, 15000, 5000, 0],
            "alt_points_ratio": [(0.04, 0.05), (0.35, 0.05), (0.60, 0.45), (0.80, 0.75), (0.95, 0.98)],
            "boxes": [
                ("FAN DISK EXPLOSION", "FL370 (37,000 FT)", (0, 200, 255)),
                ("HYDRAULIC PRESSURE", "SYSTEM 1, 2, 3 (0 PSI)", (255, 60, 60)),
                ("CONTROL METHOD", "ASYMMETRIC THROTTLES", (255, 200, 0)),
                ("TOUCHDOWN SINK RATE", "-1,620 FPM HARD IMPACT", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // UNITED AIRLINES FLIGHT 232",
            "subtitle": "SYSTEM: TAIL NO. 2 ENGINE TITANIUM FAN DISK UNCONTAINED DISINTEGRATION",
            "left_label": "TRIPLE HYDRAULIC PRESSURE (SYSTEM 1, 2, 3)",
            "left_value": "INDICATED: 0 PSI (TOTAL LOSS)",
            "left_needle_angle": -60,
            "left_desc": "High-velocity titanium fragments severed all three independent hydraulic lines.",
            "right_label": "FLIGHT CONTROL SURFACES (ELEVATOR/AILERON)",
            "right_value": "ACTUAL: 0% PHYSICAL AUTHORITY",
            "right_needle_angle": -60,
            "right_desc": "COMPLETE HYDRAULIC COLLAPSE - DIFFERENTIAL ENGINE THROTTLES ONLY REMAINING CONTROL"
        },
        "wiki_clean_queries": ["United Airlines DC-10", "United Airlines DC-10-10", "N1819U"],
        "wiki_crash_queries": ["United 232 wreckage Sioux City", "United Airlines Flight 232 crash site", "N1819U wreckage"]
    },
    "spanair_5022": {
        "match_keys": ["spanair", "5022", "madrid", "barajas", "silent wingtip", "undeployed flaps", "lemd", "gclp"],
        "flight_name": "Spanair Flight 5022",
        "aircraft_type": "McDonnell Douglas MD-82",
        "aircraft_short": "MD-82",
        "aircraft_category": "narrowbody_jet",
        "departure_airport": "Madrid-Barajas (LEMD)",
        "destination_airport": "Gran Canaria (GCLP)",
        "climate": "HOT",
        "airline": "Spanair",
        "allowed_airlines": ["Spanair", "Star Alliance"],
        "prohibited_airlines": ["Ryanair", "Air Nostrum", "Turkish Airlines", "United Airlines", "Delta", "KLM", "Lufthansa", "Buzz"],
        "prohibited_keywords": ["snow", "winter", "ice", "blizzard", "cairo", "red sea", "sharm", "museum", "hangar", "diagram", "slide", "metro", "subway", "propeller", "atr", "acrobatic", "cessna"],
        "atc_station": "MADRID TOWER // BARAJAS DEPARTURE (LEMD)",
        "investigating_agency": "CIAIAC (Comisión de Investigación de Accidentes e Incidentes de Aviación Civil)",
        "probable_cause": "Unconfigured takeoff (Flaps/Slats retracted) & TOWS audible warning failure",
        "critical_factors": [
            ("WING CONFIGURATION", "Flaps and slats in 0° retracted position during takeoff run"),
            ("TAKEOFF WARNING SYSTEM", "TOWS horn failed to sound due to faulty relay R2-5"),
            ("COCKPIT CHECKLIST", "Crew omitted takeoff flaps check during taxi interruptions"),
            ("IMPACT LOCATION", "Stalled at 40 ft; impacted terrain right of Runway 36L")
        ],
        "cvr_dialogues": [
            ("Takeoff power set. Autothrottle engaged.", "Airspeed alive, eighty knots. Crosscheck."),
            ("V1... Rotate. Positive rate.", "Stick shaker! Bank angle! What is that?"),
            ("Autopilot disconnect! Control column shaking!", "STALL! PULL UP! BANK ANGLE!")
        ],
        "atc_dialogues": [
            "Spanair 5022, cleared for takeoff runway 36L, wind calm.",
            "Spanair 5022, climb straight ahead to five thousand feet.",
            "Spanair 5022, Madrid Tower, verify status? Emergency vehicles dispatched!"
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // SPANAIR FLIGHT 5022",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS MD-82   |   RADAR STATION: MADRID TOWER (LEMD)",
            "runway": "RUNWAY 36L",
            "impact_point": "RUNWAY 36L RAVINE, BARAJAS",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // LIFT LOSS UPON ROTATION",
            "alt_steps": [500, 300, 200, 100, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.25, 0.95), (0.60, 0.92), (0.75, 0.88), (0.95, 0.98)],
            "boxes": [
                ("ROTATION SPEED", "154 KTS (VR)", (0, 200, 255)),
                ("PEAK ALTITUDE", "40 FT (12 METERS)", (255, 60, 60)),
                ("STICK SHAKER", "ACTIVATED 3 SEC POST-LIFTOFF", (255, 200, 0)),
                ("BANK ANGLE ROLL", "32° RIGHT WING STALL", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // SPANAIR FLIGHT 5022",
            "subtitle": "SYSTEM: McDONNELL DOUGLAS MD-82 TAKEOFF WARNING SYSTEM (TOWS) & FLAPS",
            "left_label": "INDICATED FLAP/SLAT POSITION",
            "left_value": "FLAPS: 0° / SLATS: RETRACTED",
            "left_needle_angle": -60,
            "left_desc": "Flap handle remained in UP/RET position; crew failed to set 11° takeoff flaps.",
            "right_label": "TAKEOFF WARNING AUDIBLE HORN (TOWS)",
            "right_value": "HORN: SILENT (CIRCUIT RELAY R2-5 FAIL)",
            "right_needle_angle": -60,
            "right_desc": "CRITICAL TOWS FAILURE - AUDIBLE ALARM NEVER SOUNDED UPON ADVANCING THROTTLES"
        },
        "wiki_clean_queries": ["Spanair MD-82", "EC-HFP", "Spanair McDonnell Douglas MD-82"],
        "wiki_crash_queries": ["Spanair Flight 5022 wreckage", "Spanair 5022 crash site Barajas", "Spanair 5022 CIAIAC", "EC-HFP wreckage"]
    },
    "northwest_255": {
        "match_keys": ["northwest 255", "flight 255", "detroit", "romulus", "undeployed flaps"],
        "flight_name": "Northwest Airlines Flight 255",
        "aircraft_type": "McDonnell Douglas MD-82",
        "aircraft_short": "MD-82",
        "aircraft_category": "narrowbody_jet",
        "departure_airport": "Detroit Metropolitan (DTW)",
        "destination_airport": "Phoenix Sky Harbor (PHX)",
        "climate": "NEUTRAL",
        "airline": "Northwest Airlines",
        "allowed_airlines": ["Northwest Airlines", "Northwest"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Ryanair", "KLM", "Lufthansa"],
        "prohibited_keywords": ["museum", "hangar", "diagram", "slide", "metro", "subway", "propeller", "atr", "acrobatic"],
        "atc_station": "DETROIT TOWER // METRO DEPARTURE (DTW)",
        "investigating_agency": "NTSB (NATIONAL TRANSPORTATION SAFETY BOARD)",
        "probable_cause": "Failure to use the taxi checklist to ensure flaps and slats were extended for takeoff",
        "critical_factors": [
            ("WING CONFIGURATION", "Flaps & slats completely retracted during takeoff roll"),
            ("CIRCUIT BREAKER P-40", "Takeoff warning system circuit breaker had no electrical power"),
            ("STALL UPON ROTATION", "Aircraft rolled violently past runway 3C and struck light poles"),
            ("SOLE SURVIVOR", "4-year-old Cecelia Cichan was sole survivor among 155 aboard")
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // NORTHWEST AIRLINES FLIGHT 255",
            "subtitle": "AIRCRAFT: McDONNELL DOUGLAS MD-82   |   RADAR STATION: DETROIT METRO ATC (DTW)",
            "runway": "RUNWAY 03C",
            "impact_point": "MIDDLEBELT ROAD / I-94",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // PREMATURE STALL POST-ROTATION",
            "alt_steps": [400, 300, 200, 100, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.30, 0.95), (0.60, 0.90), (0.80, 0.85), (0.95, 0.98)],
            "boxes": [
                ("ROTATION SPEED", "169 KTS (VR)", (0, 200, 255)),
                ("PEAK ALTITUDE", "48 FT AGL", (255, 60, 60)),
                ("ROLL OSCILLATION", "35° LEFT / 35° RIGHT", (255, 200, 0)),
                ("TOWS STATUS", "CIRCUIT BREAKER UNPOWERED", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // NORTHWEST FLIGHT 255",
            "subtitle": "SYSTEM: McDONNELL DOUGLAS MD-82 FLAP/SLAT CONTROLS & TOWS BUS",
            "left_label": "INDICATED FLAP POSITION",
            "left_value": "FLAPS: 0° (UNEXTENDED)",
            "left_needle_angle": -60,
            "left_desc": "Crew initiated takeoff roll with clean wings; flap handle remained in retracted slot.",
            "right_label": "TAKEOFF WARNING POWER BUS",
            "right_value": "CIRCUIT BREAKER: TRIPPED / DEAD",
            "right_needle_angle": -60,
            "right_desc": "NO WARNING AUDIO - P-40 POWER BUS FAILED TO ENERGIZE TAKEOFF CONFIGURATION HORN"
        },
        "wiki_clean_queries": ["Northwest Airlines MD-82", "N312RC", "Northwest Airlines McDonnell Douglas MD-82"],
        "wiki_crash_queries": ["Northwest 255 wreckage", "Northwest Flight 255 crash site Detroit", "Northwest 255 NTSB investigation"]
    },
    "qantas_72": {
        "match_keys": ["qantas 72", "qantas flight 72", "uncommanded pitch", "learmonth", "airbus a330", "adiru"],
        "flight_name": "Qantas Flight 72",
        "aircraft_type": "Airbus A330-303",
        "aircraft_short": "A330-300",
        "aircraft_category": "widebody_jet",
        "departure_airport": "Singapore Changi (SIN)",
        "destination_airport": "Perth Airport (PER)",
        "climate": "TROPICAL",
        "airline": "Qantas",
        "allowed_airlines": ["Qantas"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Ryanair", "Emirates"],
        "prohibited_keywords": ["museum", "hangar", "diagram", "metro", "train", "propeller", "acrobatic"],
        "atc_station": "PERTH CONTROL // WESTERN AUSTRALIA RADAR",
        "investigating_agency": "ATSB (AUSTRALIAN TRANSPORT SAFETY BUREAU)",
        "probable_cause": "Single-event upset corrupted ADIRU Unit 1 triggering uncommanded nose-down elevator commands",
        "critical_factors": [
            ("ADIRU 1 GLITCH", "Single event upset corrupted angle of attack (AOA) spikes"),
            ("PRIMARY FLIGHT COMPUTER", "FCPC triggered uncommanded nose-down elevator commands"),
            ("HIGH NEGATIVE G-FORCES", "Unbelted occupants thrown violently against the cabin ceiling"),
            ("EMERGENCY RECOVERY", "Crew executed manual emergency landing at RAAF Learmonth")
        ],
        "cvr_dialogues": [
            ("Cruising at FL370, weather is clear ahead.", "Autopilot 1 in command, systems nominal."),
            ("What happened? Master warning! Nav ADIRU fault!", "Aircraft is pitching down! Disconnecting autopilot!"),
            ("Pulling back on sidestick, no response!", "PULL UP! TERRAIN! LEVEL OFF!")
        ],
        "atc_dialogues": [
            "Qantas 72, Perth Control, radar contact FL370.",
            "Mayday, Mayday, Mayday, Qantas 72, uncommanded pitch down!",
            "Qantas 72, Perth, cleared direct Learmonth runway 36, descend at pilot's discretion."
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // QANTAS FLIGHT 72",
            "subtitle": "AIRCRAFT: AIRBUS A330-303   |   RADAR STATION: PERTH ATC / LEARMONTH",
            "runway": "CRUISE FL370",
            "impact_point": "RAAF LEARMONTH (EMERGENCY LANDING)",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // UNCOMMANDED PITCH OSCILLATION",
            "alt_steps": [37000, 30000, 20000, 10000, 0],
            "alt_points_ratio": [(0.04, 0.10), (0.35, 0.10), (0.50, 0.35), (0.75, 0.65), (0.95, 0.98)],
            "boxes": [
                ("CRUISE ALTITUDE", "FL370 (37,000 FT)", (0, 200, 255)),
                ("PITCH ANGLE DIVE", "-8.4° UNCOMMANDED DIVE", (255, 60, 60)),
                ("ACCELERATION LOAD", "-0.8G TO +1.56G SPIKE", (255, 200, 0)),
                ("ADIRU STATUS", "CORRUPTED DATA STREAM", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // QANTAS FLIGHT 72",
            "subtitle": "SYSTEM: AIRBUS A330 AIR DATA INERTIAL REFERENCE UNIT (ADIRU 1)",
            "left_label": "INDICATED ANGLE OF ATTACK (AOA)",
            "left_value": "AOA: 50.6° (FALSE SPIKE)",
            "left_needle_angle": 60,
            "left_desc": "Corrupted data packet sent spurious extreme high AOA reading to flight control computers.",
            "right_label": "FLIGHT CONTROL PRIMARY COMPUTER (FCPC)",
            "right_value": "ELEVATOR: NOSE-DOWN OVERRIDE",
            "right_needle_angle": -60,
            "right_desc": "FLY-BY-WIRE COMPUTER PUSHED ELEVATORS DOWN TO PREVENT IMAGINARY STALL - SEVERE VIOLENT DIVE"
        },
        "wiki_clean_queries": ["Qantas Airbus A330", "VH-QPA", "Qantas A330-300"],
        "wiki_crash_queries": ["Qantas Flight 72 Learmonth", "Qantas 72 interior damage ATSB", "VH-QPA emergency landing"]
    },
    "fine_air_101": {
        "match_keys": ["fine air 101", "fine air", "tail-heavy", "miami dc-8", "palmetto expressway"],
        "flight_name": "Fine Air Flight 101",
        "aircraft_type": "Douglas DC-8-61F",
        "aircraft_short": "DC-8",
        "aircraft_category": "widebody_jet",
        "departure_airport": "Miami International (MIA)",
        "destination_airport": "Santo Domingo (SDQ)",
        "climate": "HOT",
        "airline": "Fine Air",
        "allowed_airlines": ["Fine Air"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Ryanair", "KLM", "Lufthansa"],
        "prohibited_keywords": ["snow", "winter", "ice", "blizzard", "museum", "hangar", "diagram", "slide", "metro", "subway"],
        "atc_station": "MIAMI TOWER // MIA DEPARTURE",
        "investigating_agency": "NTSB (NATIONAL TRANSPORTATION SAFETY BOARD)",
        "probable_cause": "Improper cargo loading shifting center of gravity beyond aft limits and mis-set stabilizer trim",
        "critical_factors": [
            ("CARGO MISDISTRIBUTION", "Pallets loaded without scale; CG far aft of allowable limit"),
            ("STABILIZER MIS-TRIM", "Elevator stabilizer trim set based on false forward-CG manifest"),
            ("EXTREME PITCH-UP", "Severe pitch-up upon rotation led to unrecoverable low-altitude stall"),
            ("IMPACT SITE", "Crashed across NW 72nd Ave and NW 25th St near Miami runway 27R")
        ],
        "cvr_dialogues": [
            ("Set takeoff EPR, rolling runway 27R.", "EPR 1.88, airspeed 80 knots, instruments nominal."),
            ("Rotate... Whoa! Pitch is too high! Nose down!", "Push it down! Full forward yoke!"),
            ("Controls won't respond, we're stalling!", "FULL POWER! PUSH NOSE DOWN! BANK ANGLE!")
        ],
        "atc_dialogues": [
            "Fine Air 101 heavy, cleared for takeoff runway 27R, wind 110 at 8.",
            "Fine Air 101 heavy, contact departure on 119.4.",
            "Fine Air 101, Miami Tower... Alert 3, crash on 72nd Avenue!"
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // FINE AIR FLIGHT 101",
            "subtitle": "AIRCRAFT: DOUGLAS DC-8-61F   |   RADAR STATION: MIAMI TOWER ATC (MIA)",
            "runway": "RUNWAY 27R",
            "impact_point": "NW 72nd AVENUE / PALMETTO",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // AFT CG TAKEOFF ROTATION STALL",
            "alt_steps": [600, 450, 300, 150, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.35, 0.95), (0.65, 0.85), (0.80, 0.80), (0.95, 0.98)],
            "boxes": [
                ("ROTATION PITCH", "+29° NOSE-HIGH SPIKE", (0, 200, 255)),
                ("PEAK ALTITUDE", "520 FT AGL", (255, 60, 60)),
                ("AIRSPEED LOSS", "DROPPED BELOW VMC (120 KTS)", (255, 200, 0)),
                ("CG DISPLACEMENT", "FAR AFT OF REAR LIMIT", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // FINE AIR FLIGHT 101",
            "subtitle": "SYSTEM: DOUGLAS DC-8 HORIZONTAL STABILIZER TRIM & CARGO WEIGHT/BALANCE",
            "left_label": "INDICATED STABILIZER TRIM SETTING",
            "left_value": "TRIM: 2.4 UNITS NOSE-UP (FALSE)",
            "left_needle_angle": 30,
            "left_desc": "Crew dialed stabilizer trim based on falsified load sheet assuming 28% MAC.",
            "right_label": "ACTUAL PHYSICAL CENTER OF GRAVITY",
            "right_value": "ACTUAL CG: 38% MAC (EXTREME AFT)",
            "right_needle_angle": 65,
            "right_desc": "EXTREME AFT CENTER OF GRAVITY - CONTROL COLUMN FULL FORWARD WAS INSUFFICIENT TO PREVENT STALL"
        },
        "wiki_clean_queries": ["Fine Air DC-8", "N27UA", "Douglas DC-8 Fine Air"],
        "wiki_crash_queries": ["Fine Air 101 wreckage Miami", "Fine Air Flight 101 crash site", "N27UA wreckage NTSB"]
    },
    "crossair_498": {
        "match_keys": ["crossair 498", "sixty seconds", "nassenwil", "zurich", "saab 340"],
        "flight_name": "Crossair Flight 498",
        "aircraft_type": "Saab 340B",
        "aircraft_short": "Saab 340",
        "aircraft_category": "turboprop",
        "departure_airport": "Zurich Kloten (ZRH)",
        "destination_airport": "Dresden Airport (DRS)",
        "climate": "FOG",
        "departure_time": "08:54 AM LOCAL (MORNING FREEZING FOG & OVERCAST)",
        "airline": "Crossair",
        "allowed_airlines": ["Crossair", "Swissair"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Ryanair", "KLM", "Lufthansa"],
        "prohibited_keywords": [
            "cessna", "c172", "piper", "single engine", "light aircraft", "propeller aircraft",
            "night city", "neon", "skyline", "skyscraper", "city lights", "traffic",
            "museum", "hangar", "diagram", "slide", "metro", "subway", "jet", "airbus", "boeing"
        ],
        "atc_station": "ZURICH DEPARTURE // SWISS ATC (ZRH)",
        "investigating_agency": "AAIB / FOCA (SWISS AIRCRAFT ACCIDENT INVESTIGATION BUREAU)",
        "probable_cause": "Spatial disorientation (somatogravic illusion) causing captain to roll right into terrain",
        "critical_factors": [
            ("SPATIAL ILLUSION", "Captain reacted to non-standard Western/Soviet attitude indicators"),
            ("UNNOTICED BANK", "Aircraft entered fatal 137° spiral dive into field in Nassenwil"),
            ("CRM SILENCE", "First Officer failed to intervene as aircraft rolled right into terrain"),
            ("SWISS BFU REPORT", "Official report confirmed lack of spatial awareness in zero-visibility fog")
        ],
        "cvr_dialogues": [
            ("Climb five thousand. Following standard departure.", "Checking airspeed, passing two thousand feet."),
            ("Why is the attitude indicator rolling left?", "Turning left, turning left! Bank angle!"),
            ("Lövye sola gelmiyor! Horizon is spinning!", "PULL UP! TERRAIN AHEAD! BANK ANGLE!")
        ],
        "atc_dialogues": [
            "Crossair 498, radar contact. Climb and maintain five thousand feet.",
            "Crossair 498, verify heading two eight zero? Radar shows right turn!",
            "Crossair 498, radar contact lost. Turn immediately! Crossair 498, do you read?"
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // CROSSAIR FLIGHT 498",
            "subtitle": "AIRCRAFT: SAAB 340B   |   RADAR STATION: ZURICH DEPARTURE (ZRH)",
            "runway": "RUNWAY 28",
            "impact_point": "NASSENWIL, SWITZERLAND",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // FATAL RIGHT-HAND SPIRAL DIVE",
            "alt_steps": [4000, 3000, 2000, 1000, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.35, 0.45), (0.60, 0.35), (0.80, 0.65), (0.95, 0.98)],
            "boxes": [
                ("DEPARTURE TURN", "CLEARED LEFT -> TURNED RIGHT", (0, 200, 255)),
                ("BANK ANGLE OVERBANK", "137° RIGHT SPIRAL DIVE", (255, 60, 60)),
                ("IMPACT VELOCITY", "285 KTS NOSE DOWN", (255, 200, 0)),
                ("FLIGHT DURATION", "2 MIN 17 SEC TOTAL", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // CROSSAIR FLIGHT 498",
            "subtitle": "SYSTEM: SAAB 340B ARTIFICIAL HORIZON (ADI) & SPATIAL DISORIENTATION",
            "left_label": "CAPTAIN MENTAL PICTURE (SOVIET ADI)",
            "left_value": "PERCEIVED: BANKING STEEP LEFT",
            "left_needle_angle": -45,
            "left_desc": "Captain was trained on Soviet attitude indicators where aircraft silhouette rolls.",
            "right_label": "ACTUAL WESTERN ADI INDICATION",
            "right_value": "ACTUAL BANK: 137° STEEP RIGHT",
            "right_needle_angle": 65,
            "right_desc": "DISASTROUS SENSORY OVERLOAD - CAPTAIN CONTINUED RIGHT YOKE DEFLECTION INTO GROUND"
        },
        "wiki_clean_queries": ["Crossair Saab 340", "HB-AKK", "Saab 340 Crossair"],
        "wiki_crash_queries": ["Nassenwil", "Niederhasli", "Crossair 498", "HB-AKK"]
    },
    "bea_548": {
        "match_keys": ["bea 548", "british european 548", "four minutes", "staines", "trident", "droop flaps"],
        "flight_name": "BEA Flight 548",
        "aircraft_type": "Hawker Siddeley Trident 1C",
        "aircraft_short": "Trident 1C",
        "aircraft_category": "narrowbody_jet",
        "departure_airport": "London Heathrow (LHR)",
        "destination_airport": "Brussels Airport (BRU)",
        "climate": "NEUTRAL",
        "airline": "British European Airways",
        "allowed_airlines": ["BEA", "British European Airways", "British Airways"],
        "prohibited_airlines": ["Turkish Airlines", "United Airlines", "Delta", "Ryanair", "KLM", "Lufthansa"],
        "prohibited_keywords": ["museum", "hangar", "diagram", "slide", "metro", "subway", "propeller", "atr", "acrobatic"],
        "atc_station": "HEATHROW TOWER // LONDON CONTROL (LHR)",
        "investigating_agency": "AAIB (AIR ACCIDENTS INVESTIGATION BRANCH - UK)",
        "probable_cause": "Premature retraction of the droop leading-edge flaps resulting in deep aerodynamic stall",
        "critical_factors": [
            ("DROOP FLAPS RETRACTION", "Leading-edge droop levers operated prematurely at 1,740 ft"),
            ("DEEP STALL (SUPERSTALL)", "T-tail shadowed by stalled wings; elevator control lost"),
            ("STICK PUSHER INHIBIT", "Crew overrode and disconnected automatic stick pusher stall recovery"),
            ("CAPTAIN HEART EVENT", "Post-mortem revealed Captain Key suffered severe coronary episode")
        ],
        "radar": {
            "title": "TACTICAL FLIGHT RECONSTRUCTION // BEA FLIGHT 548",
            "subtitle": "AIRCRAFT: HAWKER SIDDELEY TRIDENT 1C   |   RADAR STATION: LONDON HEATHROW ATC",
            "runway": "RUNWAY 28R",
            "impact_point": "STAINES-UPON-THAMES MEADOW",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // SUPERSTALL AFTER DROOP RETRACTION",
            "alt_steps": [2500, 2000, 1500, 1000, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.35, 0.35), (0.55, 0.30), (0.75, 0.65), (0.95, 0.98)],
            "boxes": [
                ("DROOP RETRACTION", "1,740 FT (60 KTS TOO SLOW)", (0, 200, 255)),
                ("SUPERSTALL PITCH", "+31° NOSE-HIGH ATTITUDE", (255, 60, 60)),
                ("VERTICAL SINK RATE", "-4,500 FPM MEADOW IMPACT", (255, 200, 0)),
                ("STICK PUSHER", "MANUALLY INHIBITED BY CREW", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": "COCKPIT INSTRUMENT ANOMALY // BEA FLIGHT 548",
            "subtitle": "SYSTEM: HAWKER SIDDELEY TRIDENT DROOP FLAP LEVER & STICK PUSHER",
            "left_label": "AIRSPEED VS DROOP LIMIT",
            "left_value": "AIRSPEED: 162 KTS (MIN: 225 KTS)",
            "left_needle_angle": -45,
            "left_desc": "Droop lever was moved to UP position 63 knots below safe minimum droop retraction speed.",
            "right_label": "T-TAIL ELEVATOR CONTROL AUTHORITY",
            "right_value": "ELEVATOR: 0% AUTHORITY (SUPERSTALL)",
            "right_needle_angle": -60,
            "right_desc": "DEEP STALL AERODYNAMIC BLANKETING - T-TAIL ELEVATOR WAS FULLY SHADOWED BY STALLED MAIN WING"
        },
        "wiki_clean_queries": ["BEA Trident", "G-ARPI", "Hawker Siddeley Trident BEA"],
        "wiki_crash_queries": ["BEA 548 wreckage Staines", "BEA Flight 548 crash site", "G-ARPI wreckage AAIB"]
    }
}


def extract_incident_metadata(
    topic: str,
    scenes: Optional[List[Dict[str, Any]]] = None,
    script: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Konu başlığı ve sahne metinlerini derinlemesine analiz ederek
    olayın %100 doğru meta verilerini (uçak, hava yolu, havalimanı, telemetri) çıkarır.
    """
    combined_texts = [str(topic)]
    if scenes and isinstance(scenes, list) and len(scenes) > 0:
        for sc in scenes[:4]:
            combined_texts.append(str(sc.get("narration", "")))
            combined_texts.append(str(sc.get("image_prompt", "")))
            combined_texts.append(str(sc.get("text", "")))
    if script and isinstance(script, dict):
        combined_texts.append(str(script.get("title", "")))
        combined_texts.append(str(script.get("topic", "")))

    full_context = " ".join(combined_texts).lower()

    # 1. Öncelikli Kütüphane Taraması (En hassas anahtar kelimeler)
    # Türk Hava Yolları 981 için özel kontrol: 'sioux city' başlıkta geçse bile metin THY 981 ise THY 981 seçilir!
    if any(k in full_context for k in ["turkish airlines", "turkish 981", "flight 981", "ermenonville", "tc-jav", "orly", "ghendouer"]):
        return INCIDENT_DATABASE["turkish_981"]

    for inc_id, inc_data in INCIDENT_DATABASE.items():
        if inc_id == "turkish_981":
            continue
        # United 232 için yalnızca metin gerçekten Sioux City / Al Haynes veya United 232 anlatıyorsa eşleştir
        if inc_id == "united_232":
            if ("united 232" in full_context or "united airlines 232" in full_context or "al haynes" in full_context) and ("turkish" not in full_context):
                return inc_data
            continue

        match_keys = inc_data.get("match_keys", [])
        if any(mk in full_context for mk in match_keys):
            return inc_data

    # 2. Dinamik Jenerik Ayrıştırıcı (Bilinmeyen Olaylar İçin Akıllı Çıkarım)
    clean_topic = re.sub(r'["\']', '', topic).strip()
    plane_type = "Commercial Jet Airliner"
    m_plane = re.search(r'(Boeing\s*7\d{2}(?:-\w+)?|Airbus\s*A\d{3}(?:-\w+)?|McDonnell\s*Douglas\s*(?:MD|DC)-\d{1,2}|MD-\d{2}|DC-\d{1,2}|Saab\s*\d{3}\w?|ATR\s*\d{2}(?:-\w+)?|Beechcraft\s*\d{4}\w?|Lockheed\s*L-\d{4}|Trident\s*\w+)', full_context, re.IGNORECASE)
    if m_plane:
        plane_type = m_plane.group(1).title()

    airline = "Commercial Aviation"
    m_air = re.search(r'([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?\s+(?:Airlines|Airways|Air\s+Lines|Air|Cargo|Aéreas|Express))\s*(?:Flight)?\s*(\d+)?', " ".join(combined_texts))
    flight_title = clean_topic[:40]
    if m_air:
        airline = m_air.group(1).strip()
        flight_num = m_air.group(2) if m_air.group(2) else ""
        flight_title = f"{airline} {flight_num}".strip()

    airport = "Departure Airport"
    m_apt = re.search(r'(?:depart\w*|at|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Airport|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+ATC)', " ".join(combined_texts))
    if m_apt:
        airport = m_apt.group(1).strip()

    dest_airport = "Destination Airport"
    m_dest = re.search(r'(?:to|bound for|destination)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Airport|[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', " ".join(combined_texts))
    if m_dest:
        dest_airport = m_dest.group(1).strip()

    # İklim & Sıcaklık Tespiti
    climate = "NEUTRAL"
    if any(k in full_context for k in ["30-degree", "scorching", "blistering", "heat", "summer", "sunny", "30 derece", "kavurucu"]):
        climate = "HOT"
    elif any(k in full_context for k in ["blizzard", "snowstorm", "freezing", "ice", "winter", "kar", "buz", "fırtına"]):
        climate = "WINTER"
    elif any(k in full_context for k in ["night", "pitch-black", "darkness", "midnight", "gece"]):
        climate = "NIGHT"

    # Ülke ve Kaza Kırım Kurulu (Investigating Agency) Tespiti
    agency = "NATIONAL CIVIL AVIATION SAFETY BOARD (NTSB / JOINT)"
    dep_city = airport.replace("Airport", "").replace("ATC", "").strip() or "DEPARTURE"
    if any(k in full_context for k in ["spain", "madrid", "barajas", "canaria", "spanish", "lemd"]):
        agency = "CIAIAC (Comisión de Investigación de Accidentes e Incidentes de Aviación Civil)"
    elif any(k in full_context for k in ["france", "paris", "orly", "charles de gaulle", "french", "ory"]):
        agency = "BEA (Bureau d'Enquêtes et d'Analyses)"
    elif any(k in full_context for k in ["united kingdom", "heathrow", "london", "british", "staines", "scotland", "uk", "lhr"]):
        agency = "AAIB (Air Accidents Investigation Branch - UK)"
    elif any(k in full_context for k in ["switzerland", "swiss", "zurich", "geneva", "crossair", "zrh"]):
        agency = "AAIB / FOCA (Swiss Aircraft Accident Investigation Bureau)"
    elif any(k in full_context for k in ["australia", "perth", "qantas", "learmonth", "atsb"]):
        agency = "ATSB (Australian Transport Safety Bureau)"
    elif any(k in full_context for k in ["germany", "german", "frankfurt", "munich", "lufthansa"]):
        agency = "BFU (German Federal Bureau of Aircraft Accident Investigation)"
    elif any(k in full_context for k in ["egypt", "cairo", "sharm", "red sea", "egyptian"]):
        agency = "ECAA (Egyptian Civil Aviation Authority)"
    elif any(k in full_context for k in ["united states", "america", "florida", "detroit", "miami", "potomac", "chicago", "new york", "denver"]):
        agency = "NTSB (National Transportation Safety Board)"

    atc_station = f"{dep_city.upper()} TOWER // {dep_city.upper()} DEPARTURE"

    # Muhtemel Sebep (Probable Cause) & 4 Kritik Faktör Çıkarımı
    cause = "Aerodynamic loss of control and critical system anomaly during flight"
    if any(k in full_context for k in ["flap", "slat", "tows", "undeployed"]):
        cause = "Unconfigured takeoff attempted without flaps/slats extended and takeoff warning failure"
    elif any(k in full_context for k in ["spatial disorientation", "illusion", "bank roll", "somatogravic"]):
        cause = "Loss of aircraft control resulting from severe sensory spatial disorientation"
    elif any(k in full_context for k in ["cargo", "weight and balance", "tail-heavy", "center of gravity", "cg"]):
        cause = "Improper cargo loading shifting center of gravity beyond allowable limits"
    elif any(k in full_context for k in ["ice", "icing", "frozen", "pitot", "pt2"]):
        cause = "Atmospheric icing blocking flight instruments and inducing fatal thrust/airspeed errors"
    elif any(k in full_context for k in ["stall", "superstall", "droop"]):
        cause = "Aerodynamic stall upon departure with insufficient altitude for recovery"

    critical_factors = [
        ("FLIGHT CONTROL STATUS", "Primary control surfaces and configuration prior to incident"),
        ("COCKPIT PROCEDURES", "Crew checklist execution and human factors CRM communication"),
        ("SYSTEM WARNING INTEGRITY", "Audio-visual warning alerts and avionics system responses"),
        ("CRITICAL INCIDENT SITE", f"Accident sequence documented near {dep_city} airspace")
    ]

    return {
        "flight_name": flight_title,
        "aircraft_type": plane_type,
        "aircraft_short": plane_type.split()[0],
        "aircraft_category": "turboprop" if any(t in plane_type.lower() for t in ["atr", "beechcraft", "saab", "dash"]) else "jet",
        "departure_airport": airport,
        "destination_airport": dest_airport,
        "climate": climate,
        "airline": airline,
        "allowed_airlines": [airline],
        "prohibited_airlines": [],
        "prohibited_keywords": ["museum", "hangar", "diagram", "slide", "metro", "subway", "propeller" if "jet" in plane_type.lower() else "jet"],
        "atc_station": atc_station,
        "investigating_agency": agency,
        "probable_cause": cause,
        "critical_factors": critical_factors,
        "radar": {
            "title": f"TACTICAL FLIGHT RECONSTRUCTION // {flight_title.upper()}",
            "subtitle": f"AIRCRAFT: {plane_type.upper()}   |   RADAR STATION: {airport.upper()} ATC",
            "runway": "ACTIVE RUNWAY",
            "impact_point": f"INCIDENT LOCATION NEAR {dep_city.upper()}",
            "fdr_title": "FLIGHT DATA RECORDER (FDR) // TRAJECTORY & TELEMETRY",
            "alt_steps": [10000, 7500, 5000, 2500, 0],
            "alt_points_ratio": [(0.04, 0.95), (0.25, 0.40), (0.50, 0.20), (0.75, 0.50), (0.95, 0.98)],
            "boxes": [
                ("MAX ALTITUDE", "CRUISE LEVEL", (0, 200, 255)),
                ("CRITICAL VELOCITY", "AIRSPEED NOMINAL", (255, 200, 0)),
                ("FLIGHT PROFILE", "EMERGENCY DESCENT", (255, 60, 60)),
                ("SYSTEM INTEGRITY", "INVESTIGATION ACTIVE", (255, 80, 80))
            ]
        },
        "gauge": {
            "title": f"COCKPIT INSTRUMENT ANOMALY // {flight_title.upper()}",
            "subtitle": f"SYSTEM: {plane_type.upper()} FLIGHT CONTROLS & AVIONICS SUITE",
            "left_label": "PILOT INDICATED DISPLAY",
            "left_value": "TARGET VALUES: NOMINAL",
            "left_needle_angle": 30,
            "left_desc": "Cockpit instrumentation prior to critical emergency event.",
            "right_label": "ACTUAL PHYSICAL SYSTEM STATE",
            "right_value": "CRITICAL ANOMALY DETECTED",
            "right_needle_angle": -45,
            "right_desc": "FATAL SYSTEM FAILURE / CRITICAL ANOMALY RECORDED BY FDR"
        },
        "wiki_clean_queries": [f"{flight_title} aircraft", f"{airline} {plane_type}"],
        "wiki_crash_queries": [f"{flight_title} wreckage", f"{flight_title} crash site", f"{flight_title} report"]
    }


def create_radar_grid(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, rings: int = 4):
    """Askeri/Sivil hava trafik kontrol radar ağı çizer."""
    for r in range(1, rings + 1):
        rad = int(radius * (r / rings))
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(0, 60, 80), width=1)
    
    # 8 ana istikamet ekseni
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x2 = cx + int(radius * math.cos(rad))
        y2 = cy + int(radius * math.sin(rad))
        draw.line([(cx, cy), (x2, y2)], fill=(0, 50, 70), width=1)


def generate_flight_trajectory_map(
    flight_name: str,
    aircraft_type: str,
    departure_airport: str,
    output_path: str,
    radar_config: Optional[Dict[str, Any]] = None
) -> str:
    """Taktiksel radar rota haritası ve irtifa profili grafiği üretir (1920x1080)."""
    im = Image.new("RGB", (W, H), (10, 15, 24))
    draw = ImageDraw.ImageDraw(im)

    font_title = get_font(36, bold=True)
    font_sub = get_font(19, bold=False)
    font_badge = get_font(18, bold=True)
    font_data = get_font(15, bold=False)

    rc = radar_config or {}
    title_text = rc.get("title", f"TACTICAL FLIGHT RECONSTRUCTION // {flight_name.upper()}")
    sub_text = rc.get("subtitle", f"AIRCRAFT: {aircraft_type}   |   RADAR STATION: {departure_airport}   |   FDR/CVR SYNCHRONIZED")
    runway_label = rc.get("runway", "RUNWAY")
    impact_label = rc.get("impact_point", "CRITICAL IMPACT POINT")
    fdr_title = rc.get("fdr_title", "FLIGHT DATA RECORDER (FDR) // ALTITUDE & VELOCITY")
    alt_steps = rc.get("alt_steps", [10000, 7500, 5000, 2500, 0])
    alt_ratios = rc.get("alt_points_ratio", [(0.04, 0.95), (0.25, 0.40), (0.50, 0.20), (0.75, 0.50), (0.95, 0.98)])
    boxes = rc.get("boxes", [
        ("INITIAL CLIMB SPEED", "NOMINAL", (0, 200, 255)),
        ("MAX PEAK ALTITUDE", "CRUISE LEVEL", (255, 200, 0)),
        ("DESCENT SINK RATE", "-2,500 FPM", (255, 60, 60)),
        ("CREW CONTROL STATUS", "EMERGENCY ACTIVE", (255, 80, 80))
    ])

    # 1. Başlık & Meta Bilgi Paneli
    draw.rectangle([(60, 40), (W - 60, 110)], fill=(16, 24, 38))
    draw.rectangle([(60, 40), (W - 60, 44)], fill=(0, 180, 216))
    draw.text((80, 50), title_text, fill=(240, 245, 255), font=font_title)
    draw.text((80, 93), sub_text, fill=(0, 180, 216), font=font_sub)

    # 2. Sol Bölüm: Taktiksel Radar Kapsama Alanı
    radar_cx, radar_cy, radar_r = 540, 570, 400
    draw.rectangle([(60, 130), (1020, 1000)], fill=(12, 18, 28), outline=(25, 40, 60), width=2)
    create_radar_grid(draw, radar_cx, radar_cy, radar_r)

    # Pist Çizgisi
    rwy_st = (radar_cx - 160, radar_cy + 180)
    rwy_en = (radar_cx - 40, radar_cy + 60)
    draw.line([rwy_st, rwy_en], fill=(120, 140, 160), width=12)
    draw.text((rwy_st[0] - 80, rwy_st[1] + 10), runway_label, fill=(140, 160, 180), font=font_data)

    # Uçuş Rotası (Waypoints)
    pts = [
        rwy_en,
        (radar_cx, radar_cy + 20),
        (radar_cx + 80, radar_cy - 40),
        (radar_cx + 140, radar_cy - 120),
        (radar_cx + 180, radar_cy - 170),
        (radar_cx + 200, radar_cy - 210)  # Kaza/Enkaz Noktası
    ]
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i+1]], fill=(0, 220, 200), width=4)
        draw.ellipse([pts[i][0]-5, pts[i][1]-5, pts[i][0]+5, pts[i][1]+5], fill=(0, 255, 220))

    # Kaza/Enkaz İşareti (Kırmızı Hedef)
    cx_imp, cy_imp = pts[-1]
    draw.ellipse([cx_imp - 22, cy_imp - 22, cx_imp + 22, cy_imp + 22], outline=(255, 60, 60), width=3)
    draw.line([(cx_imp - 30, cy_imp), (cx_imp + 30, cy_imp)], fill=(255, 60, 60), width=2)
    draw.line([(cx_imp, cy_imp - 30), (cx_imp, cy_imp - 30 + 60)], fill=(255, 60, 60), width=2)
    draw.text((cx_imp + 32, cy_imp - 12), impact_label, fill=(255, 80, 80), font=font_badge)

    # 3. Sağ Bölüm: İrtifa & Telemetri Profili
    draw.rectangle([(1040, 130), (W - 60, 1000)], fill=(12, 18, 28), outline=(25, 40, 60), width=2)
    draw.text((1070, 155), fdr_title, fill=(240, 245, 255), font=font_badge)

    # Grafik Alanı
    g_x, g_y, g_w, g_h = 1070, 220, 750, 420
    draw.rectangle([(g_x, g_y), (g_x + g_w, g_y + g_h)], fill=(16, 24, 38), outline=(30, 45, 70), width=1)
    
    # Kılavuz Çizgileri & Dinamik İrtifa Etiketleri
    num_steps = len(alt_steps)
    for idx_step, alt_val in enumerate(alt_steps):
        line_y = g_y + int(g_h * (idx_step / max(1, num_steps - 1)))
        draw.line([(g_x, line_y), (g_x + g_w, line_y)], fill=(25, 38, 55), width=1)
        draw.text((g_x + 10, line_y + 4), f"{alt_val:,} FT", fill=(100, 130, 160), font=font_data)

    # Dinamik İrtifa Eğrisi (Oransal Koordinatlarla Çizim)
    curve_points = []
    for rx, ry in alt_ratios:
        px = g_x + int(g_w * rx)
        py = g_y + int(g_h * ry)
        curve_points.append((px, py))

    for i in range(len(curve_points) - 1):
        color = (0, 200, 255) if i < len(curve_points) // 2 else (255, 60, 60)
        draw.line([curve_points[i], curve_points[i+1]], fill=color, width=4)
        draw.ellipse([curve_points[i][0]-4, curve_points[i][1]-4, curve_points[i][0]+4, curve_points[i][1]+4], fill=color)

    # Telemetri Kutu Verileri (4 Kart)
    for b_idx, (b_title, b_val, b_col) in enumerate(boxes[:4]):
        bx = 1070 + (b_idx % 2) * 385
        by = 680 + (b_idx // 2) * 140
        draw.rectangle([(bx, by), (bx + 365, by + 120)], fill=(16, 24, 38), outline=(30, 45, 70), width=1)
        draw.text((bx + 20, by + 18), b_title, fill=(130, 150, 180), font=font_data)
        draw.text((bx + 20, by + 48), b_val, fill=b_col, font=get_font(24, bold=True))

    im.save(output_path, "PNG")
    return output_path


def generate_flight_telemetry_gauge(
    flight_name: str,
    aircraft_type: str,
    output_path: str,
    gauge_config: Optional[Dict[str, Any]] = None
) -> str:
    """Kokpit kadranı ve sistem anomalisi telemetri grafiği üretir (1920x1080)."""
    im = Image.new("RGB", (W, H), (10, 15, 24))
    draw = ImageDraw.ImageDraw(im)

    font_title = get_font(36, bold=True)
    font_sub = get_font(19, bold=False)
    font_badge = get_font(21, bold=True)
    font_gauge_lbl = get_font(23, bold=True)
    font_data = get_font(17, bold=False)

    gc = gauge_config or {}
    title_text = gc.get("title", f"COCKPIT INSTRUMENT ANOMALY // {flight_name.upper()}")
    sub_text = gc.get("subtitle", f"SYSTEM: {aircraft_type} FLIGHT CONTROLS & SENSOR SUITE   |   NTSB / CVR RECONSTRUCTION")
    left_lbl = gc.get("left_label", "PILOT INDICATED DISPLAY (COCKPIT GAUGES)")
    left_val = gc.get("left_value", "TARGET THRUST: NOMINAL")
    left_desc = gc.get("left_desc", "Pilots set flight controls based on indicated instruments.")
    left_angle = gc.get("left_needle_angle", 45)

    right_lbl = gc.get("right_label", "ACTUAL PHYSICAL POWER / FLIGHT DYNAMICS")
    right_val = gc.get("right_value", "CRITICAL ANOMALY: FATAL DEFICIT")
    right_desc = gc.get("right_desc", "CRITICAL FLIGHT DEFICIT RECORDED BY ACCIDENT INVESTIGATION")
    right_angle = gc.get("right_needle_angle", -45)

    # 1. Başlık
    draw.rectangle([(60, 40), (W - 60, 110)], fill=(16, 24, 38))
    draw.rectangle([(60, 40), (W - 60, 44)], fill=(255, 90, 95))
    draw.text((80, 50), title_text, fill=(240, 245, 255), font=font_title)
    draw.text((80, 93), sub_text, fill=(255, 120, 120), font=font_sub)

    # 2. Sol Kadran: Gösterge / Pilotun Algısı
    draw.rectangle([(60, 140), (940, 980)], fill=(14, 20, 32), outline=(35, 50, 75), width=2)
    draw.text((100, 175), left_lbl, fill=(200, 220, 240), font=font_badge)

    g1_cx, g1_cy, g1_r = 500, 540, 260
    draw.ellipse([g1_cx - g1_r, g1_cy - g1_r, g1_cx + g1_r, g1_cy + g1_r], fill=(18, 26, 42), outline=(60, 80, 110), width=4)
    for a in range(-120, 130, 25):
        rad = math.radians(a - 90)
        p1 = (g1_cx + int((g1_r - 25) * math.cos(rad)), g1_cy + int((g1_r - 25) * math.sin(rad)))
        p2 = (g1_cx + int(g1_r * math.cos(rad)), g1_cy + int(g1_r * math.sin(rad)))
        draw.line([p1, p2], fill=(180, 200, 220), width=3)
    
    # Sol Kadran İbresi
    i1_rad = math.radians(left_angle - 90)
    i1_tip = (g1_cx + int((g1_r - 40) * math.cos(i1_rad)), g1_cy + int((g1_r - 40) * math.sin(i1_rad)))
    draw.line([(g1_cx, g1_cy), i1_tip], fill=(0, 220, 180), width=7)
    draw.ellipse([g1_cx - 18, g1_cy - 18, g1_cx + 18, g1_cy + 18], fill=(0, 220, 180))

    # Değer & Açıklama
    draw.text((g1_cx - 180, g1_cy + 130), left_val, fill=(0, 240, 200), font=font_gauge_lbl)
    draw.text((100, 890), left_desc[:85], fill=(150, 170, 190), font=font_data)

    # 3. Sağ Kadran: Gerçek Durum / Tehlikeli Anomali
    draw.rectangle([(980, 140), (W - 60, 980)], fill=(14, 20, 32), outline=(35, 50, 75), width=2)
    draw.text((1020, 175), right_lbl, fill=(255, 120, 120), font=font_badge)

    g2_cx, g2_cy, g2_r = 1420, 540, 260
    draw.ellipse([g2_cx - g2_r, g2_cy - g2_r, g2_cx + g2_r, g2_cy + g2_r], fill=(18, 26, 42), outline=(80, 40, 50), width=4)
    for a in range(-120, 130, 25):
        rad = math.radians(a - 90)
        p1 = (g2_cx + int((g2_r - 25) * math.cos(rad)), g2_cy + int((g2_r - 25) * math.sin(rad)))
        p2 = (g2_cx + int(g2_r * math.cos(rad)), g2_cy + int(g2_r * math.sin(rad)))
        draw.line([p1, p2], fill=(180, 140, 150), width=3)

    # Sağ Kadran İbresi
    i2_rad = math.radians(right_angle - 90)
    i2_tip = (g2_cx + int((g2_r - 40) * math.cos(i2_rad)), g2_cy + int((g2_r - 40) * math.sin(i2_rad)))
    draw.line([(g2_cx, g2_cy), i2_tip], fill=(255, 60, 60), width=7)
    draw.ellipse([g2_cx - 18, g2_cy - 18, g2_cx + 18, g2_cy + 18], fill=(255, 60, 60))

    draw.text((g2_cx - 180, g2_cy + 130), right_val, fill=(255, 80, 80), font=font_gauge_lbl)
    draw.text((1020, 890), right_desc[:85], fill=(255, 140, 140), font=font_data)

    im.save(output_path, "PNG")
    return output_path


def _draw_airplane_vector(heading_deg: float, size: int = 76) -> Image.Image:
    """Yolcu uçaklarındaki IFE (In-Flight Entertainment) ekranlarına özgü şık 2D/2.5D jetliner ikonu çizer."""
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    cx, cy = size // 2, size // 2
    # Ana Gövde (Fuselage)
    d.polygon([
        (cx, 6), (cx + 5, 20), (cx + 5, size - 16),
        (cx, size - 8), (cx - 5, size - 16), (cx - 5, 20)
    ], fill=(255, 255, 255, 250))
    # Burun Radom Çizgisi
    d.polygon([(cx - 4, 18), (cx + 4, 18), (cx, 8)], fill=(0, 220, 255, 255))
    # Ana Kanatlar (Swept Wings)
    d.polygon([
        (cx, 26), (size - 6, 46), (size - 8, 52),
        (cx, 38), (8, 52), (6, 46)
    ], fill=(0, 210, 255, 240))
    # Jet Motorları (Nacelles)
    d.rectangle([(cx - 16, 36), (cx - 11, 47)], fill=(200, 220, 240, 255))
    d.rectangle([(cx + 11, 36), (cx + 16, 47)], fill=(200, 220, 240, 255))
    # Yatay Stabilizatörler (Tailplane)
    d.polygon([
        (cx, size - 18), (size - 18, size - 10), (size - 20, size - 6),
        (cx, size - 12), (20, size - 6), (18, size - 10)
    ], fill=(0, 180, 230, 240))
    # Seyir / Seyirfeneri Işıkları (Nav Lights): Sağ Yeşil, Sol Kırmızı
    d.ellipse([(size - 7, 44), (size - 2, 49)], fill=(16, 240, 129, 255))
    d.ellipse([(2, 44), (7, 49)], fill=(255, 50, 50, 255))
    return icon.rotate(-heading_deg, resample=Image.Resampling.BILINEAR, expand=False)


def generate_animated_flight_path_video(
    flight_name: str,
    aircraft_type: str,
    departure_airport: str,
    output_path: str,
    radar_config: Optional[Dict[str, Any]] = None,
    destination_airport: str = "Destination Airport",
    climate: str = "NEUTRAL",
    duration: float = 6.0,
    fps: int = 25,
    width: int = 1920,
    height: int = 1080
) -> str:
    """
    Yolcu Uçakları İçi Eğlence Ekranı (In-Flight Entertainment - IFE / Airshow 2.5D Harita):
    Kabin koltuk arkası ekranlarındaki (Rockwell Collins Airshow / FlightRadar) estetiğe sahip;
    bölgesel topoğrafya haritası üzerinde süzülen 3D/2D jetliner ikonu, parlak uçuş rotası izi
    ve alt/üst uçuş telemetri barlarıyla 1080p sinematik video üretir.
    """
    import subprocess
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    rc = radar_config or {}
    dest_apt = destination_airport if destination_airport != "Destination Airport" else rc.get("destination", "DESTINATION AIRPORT")
    runway_label = rc.get("runway", "ACTIVE RUNWAY")
    impact_label = rc.get("impact_point", "CRITICAL ANOMALY / IMPACT ZONE")

    font_brand = get_font(26, bold=True)
    font_sub = get_font(16, bold=False)
    font_badge = get_font(18, bold=True)
    font_card_title = get_font(15, bold=False)
    font_card_val = get_font(24, bold=True)

    total_frames = max(25, int(duration * fps))

    # Geniş Perspektifli Rota Eğrisi (Büyük Ekran Koordinatları)
    map_x1, map_y1 = 60, 140
    map_x2, map_y2 = width - 60, height - 150

    p_origin = (280, 720)
    p_climb1 = (520, 610)
    p_climb2 = (880, 480)
    p_apex = (1220, 410)
    p_end = (1620, 560)
    pts = [p_origin, p_climb1, p_climb2, p_apex, p_end]

    dists = [0.0]
    for i in range(len(pts) - 1):
        dists.append(dists[-1] + math.hypot(pts[i+1][0] - pts[i][0], pts[i+1][1] - pts[i][1]))
    total_dist = dists[-1]

    # ffmpeg doğrudan pipe başlat
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{width}x{height}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "fast",
        "-pix_fmt", "yuv420p",
        output_path
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    alt_steps = rc.get("alt_steps", [10000, 7500, 5000, 2500, 0])
    alt_max = max(alt_steps) if alt_steps else 12000

    # Dış Sıcaklık Hesaplaması (İklim Gerçekliği)
    if climate == "HOT":
        base_temp_c = 31
    elif climate == "WINTER":
        base_temp_c = -12
    elif climate == "TROPICAL":
        base_temp_c = 28
    else:
        base_temp_c = 18

    try:
        for f in range(total_frames):
            p = f / max(1, total_frames - 1)
            # Modern derin lacivert IFE zemin (Boeing/Airbus Airshow Palette)
            im = Image.new("RGB", (width, height), (7, 14, 26))
            draw = ImageDraw.ImageDraw(im)

            # 1. Bölgesel Harita Izgarası & Enlem/Boylam Çizgileri
            for x in range(map_x1, map_x2, 140):
                draw.line([(x, map_y1), (x, map_y2)], fill=(12, 25, 45), width=1)
            for y in range(map_y1, map_y2, 110):
                draw.line([(map_x1, y), (map_x2, y)], fill=(12, 25, 45), width=1)

            # Koordinat Etiketleri (IFE Graticule Annotations)
            draw.text((map_x1 + 15, map_y1 + 15), "40°28'N  03°33'W", fill=(0, 140, 190, 160), font=get_font(12, False))
            draw.text((map_x2 - 140, map_y1 + 15), "28°08'N  15°23'W", fill=(0, 140, 190, 160), font=get_font(12, False))

            # 2. Üst IFE Bilgi Bandı (Seatback Display Header)
            draw.rectangle([(map_x1, 35), (map_x2, 115)], fill=(11, 20, 36), outline=(0, 200, 240), width=2)
            draw.rectangle([(map_x1, 35), (map_x2, 38)], fill=(0, 220, 255))
            draw.text((map_x1 + 30, 48), f"✈️ IN-FLIGHT AIRSHOW // {flight_name.upper()}", fill=(255, 255, 255), font=font_brand)
            draw.text((map_x1 + 30, 84), f"AIRCRAFT: {aircraft_type.upper()}   |   MOVING MAP FLIGHT TRACKER", fill=(0, 200, 240), font=font_sub)

            # Rota Rozeti (Kalkış ➔ Varış)
            route_badge = f"{departure_airport.upper()} ➔ {dest_apt.upper()}"
            draw.text((map_x2 - 460, 58), route_badge, fill=(255, 215, 0), font=font_badge)

            # 3. Kalkış Meydanı & Varış Meydanı Düğümleri
            draw.ellipse([p_origin[0] - 12, p_origin[1] - 12, p_origin[0] + 12, p_origin[1] + 12], fill=(0, 180, 240), outline=(255, 255, 255), width=2)
            draw.text((p_origin[0] - 80, p_origin[1] + 18), f"[ORIGIN] {departure_airport[:20]}", fill=(180, 210, 240), font=font_badge)
            draw.text((p_origin[0] - 60, p_origin[1] + 40), runway_label, fill=(120, 160, 200), font=get_font(14, False))

            draw.ellipse([p_end[0] - 12, p_end[1] - 12, p_end[0] + 12, p_end[1] + 12], fill=(16, 185, 129), outline=(255, 255, 255), width=2)
            draw.text((p_end[0] - 100, p_end[1] + 18), f"[DEST] {dest_apt[:20]}", fill=(16, 220, 150), font=font_badge)

            # 4. Rota İzi (Glowing Flight Path Ribbon)
            cur_dist = p * total_dist
            drawn_pts = []
            cur_x, cur_y = pts[0]
            heading = 65.0
            for i in range(len(pts) - 1):
                if cur_dist >= dists[i+1]:
                    drawn_pts.append(pts[i])
                    if i == len(pts) - 2:
                        drawn_pts.append(pts[i+1])
                        cur_x, cur_y = pts[i+1]
                elif cur_dist >= dists[i]:
                    drawn_pts.append(pts[i])
                    sub_ratio = (cur_dist - dists[i]) / max(0.001, (dists[i+1] - dists[i]))
                    cur_x = pts[i][0] + (pts[i+1][0] - pts[i][0]) * sub_ratio
                    cur_y = pts[i][1] + (pts[i+1][1] - pts[i][1]) * sub_ratio
                    dx_seg = pts[i+1][0] - pts[i][0]
                    dy_seg = pts[i+1][1] - pts[i][1]
                    heading = math.degrees(math.atan2(dy_seg, dx_seg)) + 90
                    drawn_pts.append((cur_x, cur_y))
                    break

            # Tamamlanan Rota Çizgisi (Neon Turkuaz & İlerledikçe Turuncu)
            for i in range(len(drawn_pts) - 1):
                col = (0, 220, 255) if i < len(drawn_pts) // 2 else (255, 160, 20)
                draw.line([drawn_pts[i], drawn_pts[i+1]], fill=col, width=4)
                # İntra-waypoint halkaları
                if i % 2 == 1:
                    draw.ellipse([drawn_pts[i][0]-5, drawn_pts[i][1]-5, drawn_pts[i][0]+5, drawn_pts[i][1]+5], fill=(255, 255, 255))

            # 5. Uçak İkonu ve 2.5D Gölgesi
            alt_ratio = p if p < 0.5 else max(0.05, 1.0 - (p - 0.5) * 1.8)
            shadow_offset = int(12 + alt_ratio * 25)
            # Yerdeki irtifa gölgesi (Projected Altitude Shadow)
            draw.ellipse([cur_x - 18, cur_y + shadow_offset - 8, cur_x + 18, cur_y + shadow_offset + 8], fill=(3, 7, 14, 180))
            draw.line([(cur_x, cur_y), (cur_x, cur_y + shadow_offset)], fill=(0, 180, 220, 80), width=1)

            # Dönen 2D Jetliner Vektörü
            plane_icon = _draw_airplane_vector(heading, size=74)
            im.paste(plane_icon, (int(cur_x - plane_icon.width // 2), int(cur_y - plane_icon.height // 2)), plane_icon)

            # Kaza / Hedef Reticle (Olay Anında Flaşör)
            if p > 0.65:
                blink = (f // 6) % 2 == 0
                ret_col = (255, 60, 60) if blink else (180, 30, 30)
                draw.ellipse([p_end[0] - 25, p_end[1] - 25, p_end[0] + 25, p_end[1] + 25], outline=ret_col, width=3)
                draw.line([(p_end[0] - 35, p_end[1]), (p_end[0] + 35, p_end[1])], fill=ret_col, width=2)
                draw.line([(p_end[0], p_end[1] - 35), (p_end[0], p_end[1] + 35)], fill=ret_col, width=2)
                draw.text((p_end[0] - 120, p_end[1] - 50), impact_label, fill=ret_col, font=font_badge)

            # 6. Alt IFE Yolcu Bilgi Çubuğu (4 Modern Uçuş Kartı)
            if p < 0.40:
                p_sub = p / 0.40
                cur_alt = int(40 + p_sub * (alt_max - 40))
                cur_ias = int(154 + p_sub * 90)
                status_txt = "NORMAL CLIMB // EN ROUTE"
                status_color = (16, 220, 150)
            elif p < 0.70:
                p_sub = (p - 0.40) / 0.30
                cur_alt = int(alt_max - p_sub * 800)
                cur_ias = int(244 - p_sub * 40)
                status_txt = "⚠️ ANOMALY DETECTED // STALL WARNING"
                status_color = (255, 180, 0)
            else:
                p_sub = (p - 0.70) / 0.30
                cur_alt = max(0, int((alt_max - 800) * (1.0 - p_sub)))
                cur_ias = int(204 + p_sub * 80)
                status_txt = "🚨 EMERGENCY // UNUSUAL ATTITUDE DETECTED"
                status_color = (255, 60, 60)

            cur_temp = int(base_temp_c - (cur_alt / 1000.0) * 1.98)
            cur_temp_f = int(cur_temp * 1.8 + 32)

            bar_y1, bar_y2 = height - 130, height - 30
            card_w = (map_x2 - map_x1 - 45) // 4
            cards = [
                ("GROUND SPEED", f"{cur_ias} KTS", f"{int(cur_ias * 1.852)} KM/H", (0, 220, 255)),
                ("ALTITUDE", f"{cur_alt:,} FT", f"{int(cur_alt * 0.3048):,} METERS", (255, 215, 0)),
                ("OUTSIDE AIR TEMP", f"{cur_temp:+d}°C", f"{cur_temp_f:+d}°F", (0, 220, 200)),
                ("FLIGHT STATUS", status_txt, "TRANSPONDER: 7700", status_color)
            ]

            for c_i, (lbl, val1, val2, c_col) in enumerate(cards):
                cx1 = map_x1 + c_i * (card_w + 15)
                cx2 = cx1 + card_w
                draw.rectangle([(cx1, bar_y1), (cx2, bar_y2)], fill=(11, 20, 36), outline=(20, 42, 68), width=1)
                # Üst aksan çizgisi
                draw.line([(cx1, bar_y1), (cx2, bar_y1)], fill=c_col, width=2)
                draw.text((cx1 + 18, bar_y1 + 12), lbl, fill=(140, 165, 190), font=font_card_title)
                draw.text((cx1 + 18, bar_y1 + 34), val1, fill=c_col, font=font_card_val)
                draw.text((cx1 + 18, bar_y1 + 68), val2, fill=(160, 180, 200), font=get_font(13, False))

            proc.stdin.write(im.tobytes())

    finally:
        proc.stdin.close()
        proc.wait()

    return output_path


def generate_flight_graphics(
    topic: str,
    work_dir: Path,
    scenes: Optional[List[Dict[str, Any]]] = None,
    script: Optional[Dict[str, Any]] = None
) -> dict:
    """Verilen olay başlığı ve sahne metinleri için her iki grafiği üretir ve yollarını döner."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    meta = extract_incident_metadata(topic, scenes=scenes, script=script)

    g1_path = str(work_dir / "flight_trajectory_map.png")
    g2_path = str(work_dir / "flight_telemetry_gauge.png")

    generate_flight_trajectory_map(
        flight_name=meta["flight_name"],
        aircraft_type=meta["aircraft_type"],
        departure_airport=meta["departure_airport"],
        output_path=g1_path,
        radar_config=meta.get("radar")
    )

    generate_flight_telemetry_gauge(
        flight_name=meta["flight_name"],
        aircraft_type=meta["aircraft_type"],
        output_path=g2_path,
        gauge_config=meta.get("gauge")
    )

    v_path = str(work_dir / "flight_path_animated.mp4")
    try:
        generate_animated_flight_path_video(
            flight_name=meta["flight_name"],
            aircraft_type=meta["aircraft_type"],
            departure_airport=meta["departure_airport"],
            output_path=v_path,
            radar_config=meta.get("radar"),
            destination_airport=meta.get("destination_airport", "Destination Airport"),
            climate=meta.get("climate", "NEUTRAL"),
            duration=6.5
        )
        print(f"[AVIATION-TELEMETRY] 🎬 '{meta['flight_name']}' için 2.5D IFE Airshow yolcu ekranı videosu üretildi.")
    except Exception as e_anim:
        print(f"[AVIATION-TELEMETRY] ⚠️ Animasyonlu radar video üretim uyarısı: {e_anim}")
        v_path = None

    print(f"[AVIATION-TELEMETRY] ✅ '{meta['flight_name']}' için radar haritası, kadran ve taktik video hazırlandı.")

    return {
        "trajectory_map": g1_path,
        "telemetry_gauge": g2_path,
        "animated_radar_video": v_path,
        "metadata": meta
    }


if __name__ == "__main__":
    test_dir = Path("/tmp/test_telemetry")
    res = generate_flight_graphics("The Sioux City Variant: When JAL Cargo 124 Lost Everything (Alternative: DC-10 Cargo Door Crisis of Turkish Airlines 981)", test_dir)
    print("Test üretimi başarılı:", res)
