import streamlit as st
import json
import os
from datetime import datetime
from collections import defaultdict
import pandas as pd
import io

# Konfiguration
st.set_page_config(
    page_title="Ernährungsplaner",
    page_icon="🍽️",
    layout="wide"
)

# Datei für Datenspeicherung
DATA_FILE = "meal_planner_data.json"

# Datenstruktur initialisieren
def load_data():
    """Lädt Daten aus JSON-Datei"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Migration von altem Format zu neuem Format
            if "wochenplan" in data and data["wochenplan"]:
                first_day = list(data["wochenplan"].values())[0]
                # Prüfe ob altes Format (dict mit Mahlzeiten)
                if isinstance(first_day, dict) and not isinstance(first_day, list):
                    print("Migriere altes Wochenplan-Format...")
                    new_wochenplan = {}
                    time_mapping = {
                        "Frühstück": "08:00",
                        "Mittagessen": "12:00",
                        "Abendessen": "18:00",
                        "Snacks": "15:00"
                    }
                    for tag, mahlzeiten in data["wochenplan"].items():
                        new_wochenplan[tag] = []
                        for mahlzeit_name, rezept in mahlzeiten.items():
                            if rezept:
                                new_wochenplan[tag].append({
                                    "zeit": time_mapping.get(mahlzeit_name, "12:00"),
                                    "rezept": rezept
                                })
                        # Sortiere nach Zeit
                        new_wochenplan[tag].sort(key=lambda x: x["zeit"])
                    data["wochenplan"] = new_wochenplan
                    # Speichere migrierte Daten
                    save_data(data)
            
            return data
    
    return {
        "zutaten": {},
        "rezepte": {},
        "wochenplan": {
            "Montag": [],
            "Dienstag": [],
            "Mittwoch": [],
            "Donnerstag": [],
            "Freitag": [],
            "Samstag": [],
            "Sonntag": []
        }
    }

def save_data(data):
    """Speichert Daten in JSON-Datei"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Hilfsfunktionen
def calculate_recipe_nutrition(rezept, zutaten):
    """Berechnet Nährwerte für ein Rezept"""
    total = {"protein": 0, "kohlenhydrate": 0, "fett": 0, "kalorien": 0}
    
    for zutat_name, menge in rezept["zutaten"].items():
        if zutat_name in zutaten:
            zutat = zutaten[zutat_name]
            faktor = menge / 100  # Umrechnung von g auf pro 100g
            total["protein"] += zutat["protein"] * faktor
            total["kohlenhydrate"] += zutat["kohlenhydrate"] * faktor
            total["fett"] += zutat["fett"] * faktor
            total["kalorien"] += zutat["kalorien"] * faktor
    
    return total

def generate_shopping_list(data):
    """Generiert Einkaufsliste aus Wochenplan"""
    einkaufsliste = defaultdict(float)
    
    for tag, mahlzeiten in data["wochenplan"].items():
        # mahlzeiten ist jetzt eine Liste von Dicts mit {zeit, rezept}
        for mahlzeit in mahlzeiten:
            rezept_name = mahlzeit.get("rezept")
            if rezept_name and rezept_name in data["rezepte"]:
                rezept = data["rezepte"][rezept_name]
                for zutat, menge in rezept["zutaten"].items():
                    einkaufsliste[zutat] += menge
    
    return dict(einkaufsliste)

# Session State initialisieren
if 'data' not in st.session_state:
    st.session_state.data = load_data()

# Hauptapp
st.title("🍽️ Ernährungsplaner")
st.markdown("---")

# Tabs für verschiedene Bereiche
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Dashboard", 
    "🥕 Zutaten", 
    "📖 Rezepte", 
    "📅 Wochenplan", 
    "🛒 Einkaufsliste"
])

# TAB 1: DASHBOARD
with tab1:
    st.header("Wochenübersicht")
    
    data = st.session_state.data
    
    # Berechne Gesamtnährwerte für die Woche
    weekly_totals = {"protein": 0, "kohlenhydrate": 0, "fett": 0, "kalorien": 0}
    meal_count = 0
    
    for tag, mahlzeiten in data["wochenplan"].items():
        # mahlzeiten ist jetzt eine Liste
        for mahlzeit in mahlzeiten:
            rezept_name = mahlzeit.get("rezept")
            if rezept_name and rezept_name in data["rezepte"]:
                meal_count += 1
                nutrition = calculate_recipe_nutrition(
                    data["rezepte"][rezept_name], 
                    data["zutaten"]
                )
                for key in weekly_totals:
                    weekly_totals[key] += nutrition[key]
    
    # Statistiken anzeigen
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Gesamt Kalorien", f"{weekly_totals['kalorien']:.0f} kcal")
    with col2:
        st.metric("Gesamt Protein", f"{weekly_totals['protein']:.1f} g")
    with col3:
        st.metric("Gesamt Kohlenhydrate", f"{weekly_totals['kohlenhydrate']:.1f} g")
    with col4:
        st.metric("Gesamt Fett", f"{weekly_totals['fett']:.1f} g")
    
    st.markdown("---")
    
    # Durchschnitt pro Tag
    if meal_count > 0:
        st.subheader("Durchschnitt pro Tag (bei vollständigem Plan)")
        daily_avg = {k: v / 7 for k, v in weekly_totals.items()}
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Ø Kalorien/Tag", f"{daily_avg['kalorien']:.0f} kcal")
        with col2:
            st.metric("Ø Protein/Tag", f"{daily_avg['protein']:.1f} g")
        with col3:
            st.metric("Ø Kohlenhydrate/Tag", f"{daily_avg['kohlenhydrate']:.1f} g")
        with col4:
            st.metric("Ø Fett/Tag", f"{daily_avg['fett']:.1f} g")
    
    st.markdown("---")
    
    # Schnellübersicht Wochenplan
    st.subheader("Geplante Mahlzeiten diese Woche")
    for tag, mahlzeiten in data["wochenplan"].items():
        if mahlzeiten:  # Nur anzeigen wenn Mahlzeiten vorhanden
            with st.expander(f"**{tag}** ({len(mahlzeiten)} Mahlzeit{'en' if len(mahlzeiten) != 1 else ''})"):
                for mahlzeit in sorted(mahlzeiten, key=lambda x: x["zeit"]):
                    st.write(f"- **{mahlzeit['zeit']} Uhr**: {mahlzeit['rezept']}")

# TAB 2: ZUTATEN
with tab2:
    st.header("Zutaten verwalten")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Neue Zutat hinzufügen")
        
        with st.form("neue_zutat"):
            zutat_name = st.text_input("Name der Zutat")
            
            col_a, col_b, col_c, col_d = st.columns(4)
            with col_a:
                protein = st.number_input("Protein (g/100g)", min_value=0.0, step=0.1, format="%.1f")
            with col_b:
                kohlenhydrate = st.number_input("Kohlenhydrate (g/100g)", min_value=0.0, step=0.1, format="%.1f")
            with col_c:
                fett = st.number_input("Fett (g/100g)", min_value=0.0, step=0.1, format="%.1f")
            with col_d:
                kalorien = st.number_input("Kalorien (kcal/100g)", min_value=0.0, step=1.0, format="%.0f")
            
            kategorie = st.selectbox(
                "Kategorie",
                ["Obst & Gemüse", "Fleisch & Fisch", "Milchprodukte", "Getreide & Backwaren", 
                 "Hülsenfrüchte", "Öle & Fette", "Gewürze & Saucen", "Sonstiges"]
            )
            
            submitted = st.form_submit_button("Zutat hinzufügen")
            
            if submitted and zutat_name:
                if zutat_name in st.session_state.data["zutaten"]:
                    st.error(f"Zutat '{zutat_name}' existiert bereits!")
                else:
                    st.session_state.data["zutaten"][zutat_name] = {
                        "protein": protein,
                        "kohlenhydrate": kohlenhydrate,
                        "fett": fett,
                        "kalorien": kalorien,
                        "kategorie": kategorie
                    }
                    save_data(st.session_state.data)
                    st.success(f"Zutat '{zutat_name}' erfolgreich hinzugefügt!")
                    st.rerun()
    
    with col2:
        st.subheader("Statistik")
        st.metric("Anzahl Zutaten", len(st.session_state.data["zutaten"]))
    
    st.markdown("---")
    
    # CSV Import
    st.subheader("📥 Zutaten aus CSV importieren")
    
    with st.expander("CSV-Import Anleitung"):
        st.write("""
        **CSV-Format:**
        Die CSV-Datei sollte folgende Spalten enthalten (mit Komma oder Semikolon getrennt):
        - `Name` - Name der Zutat
        - `Protein` - Protein in g/100g
        - `Kohlenhydrate` - Kohlenhydrate in g/100g
        - `Fette` oder `Fett` - Fett in g/100g
        - `Kcal` oder `Kalorien` - Kalorien in kcal/100g
        - `Kategorie` (optional) - Kategorie der Zutat
        
        **Beispiel:**
        ```
        Name,Protein,Kohlenhydrate,Fette,Kcal,Kategorie
        Hähnchenbrust,23.0,0.0,1.2,110,Fleisch & Fisch
        Reis,7.0,77.0,0.6,350,Getreide & Backwaren
        Brokkoli,3.0,7.0,0.4,34,Obst & Gemüse
        ```
        """)
        
        # Download Beispiel-CSV
        example_csv = "Name,Protein,Kohlenhydrate,Fette,Kcal,Kategorie\n"
        example_csv += "Hähnchenbrust,23.0,0.0,1.2,110,Fleisch & Fisch\n"
        example_csv += "Reis,7.0,77.0,0.6,350,Getreide & Backwaren\n"
        example_csv += "Brokkoli,3.0,7.0,0.4,34,Obst & Gemüse\n"
        
        st.download_button(
            label="📥 Beispiel-CSV herunterladen",
            data=example_csv,
            file_name="zutaten_beispiel.csv",
            mime="text/csv"
        )
    
    uploaded_file = st.file_uploader(
        "Wähle eine CSV-Datei aus",
        type=["csv"],
        help="CSV-Datei mit Zutaten hochladen"
    )
    
    if uploaded_file is not None:
        try:
            # Versuche verschiedene Trennzeichen
            content = uploaded_file.read().decode('utf-8')
            
            # Erkenne Trennzeichen
            if ';' in content.split('\n')[0]:
                df = pd.read_csv(io.StringIO(content), sep=';')
            else:
                df = pd.read_csv(io.StringIO(content))
            
            # Normalisiere Spaltennamen (entferne Leerzeichen, Kleinbuchstaben)
            df.columns = df.columns.str.strip().str.lower()
            
            # Mapping für verschiedene Spaltennamen
            column_mapping = {
                'name': 'Name',
                'protein': 'Protein',
                'kohlenhydrate': 'Kohlenhydrate',
                'fette': 'Fette',
                'fett': 'Fette',
                'kcal': 'Kcal',
                'kalorien': 'Kcal',
                'kategorie': 'Kategorie'
            }
            
            # Benenne Spalten um
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df.rename(columns={old_name: new_name}, inplace=True)
            
            # Prüfe erforderliche Spalten
            required = ['Name', 'Protein', 'Kohlenhydrate', 'Fette', 'Kcal']
            missing = [col for col in required if col not in df.columns]
            
            if missing:
                st.error(f"❌ Fehlende Spalten: {', '.join(missing)}")
                st.write("Gefundene Spalten:", list(df.columns))
            else:
                # Füge Kategorie hinzu, falls nicht vorhanden
                if 'Kategorie' not in df.columns:
                    df['Kategorie'] = 'Sonstiges'
                
                # Vorschau
                st.success(f"✅ CSV erfolgreich geladen: {len(df)} Zutaten gefunden")
                st.write("**Vorschau:**")
                st.dataframe(df.head(10))
                
                # Standard-Kategorie für fehlende Werte
                default_kategorie = st.selectbox(
                    "Standard-Kategorie für Zutaten ohne Kategorie",
                    ["Obst & Gemüse", "Fleisch & Fisch", "Milchprodukte", "Getreide & Backwaren", 
                     "Hülsenfrüchte", "Öle & Fette", "Gewürze & Saucen", "Sonstiges"],
                    index=7
                )
                
                # Duplikat-Handling
                existing_names = set(st.session_state.data["zutaten"].keys())
                new_names = set(df['Name'].values)
                duplicates = existing_names.intersection(new_names)
                
                if duplicates:
                    st.warning(f"⚠️ {len(duplicates)} Zutaten existieren bereits:")
                    st.write(", ".join(sorted(duplicates)))
                    
                    duplicate_action = st.radio(
                        "Was soll mit Duplikaten passieren?",
                        ["Überspringen", "Überschreiben"],
                        horizontal=True
                    )
                else:
                    duplicate_action = "Überspringen"
                
                # Import-Button
                col_import1, col_import2 = st.columns([1, 3])
                with col_import1:
                    if st.button("✅ Zutaten importieren", type="primary"):
                        imported = 0
                        skipped = 0
                        errors = []
                        
                        for idx, row in df.iterrows():
                            try:
                                name = str(row['Name']).strip()
                                
                                # Prüfe Duplikat
                                if name in existing_names:
                                    if duplicate_action == "Überspringen":
                                        skipped += 1
                                        continue
                                
                                # Kategorie handling
                                kategorie = row.get('Kategorie', default_kategorie)
                                if pd.isna(kategorie) or kategorie == '':
                                    kategorie = default_kategorie
                                
                                # Erstelle Zutat
                                st.session_state.data["zutaten"][name] = {
                                    "protein": float(row['Protein']),
                                    "kohlenhydrate": float(row['Kohlenhydrate']),
                                    "fett": float(row['Fette']),
                                    "kalorien": float(row['Kcal']),
                                    "kategorie": kategorie
                                }
                                imported += 1
                                
                            except Exception as e:
                                errors.append(f"Zeile {idx + 2}: {str(e)}")
                        
                        # Speichern
                        save_data(st.session_state.data)
                        
                        # Feedback
                        if imported > 0:
                            st.success(f"✅ {imported} Zutaten erfolgreich importiert!")
                        if skipped > 0:
                            st.info(f"ℹ️ {skipped} Zutaten übersprungen (bereits vorhanden)")
                        if errors:
                            st.error("❌ Fehler beim Import:")
                            for error in errors[:5]:  # Zeige maximal 5 Fehler
                                st.write(f"- {error}")
                        
                        st.rerun()
                
                with col_import2:
                    if st.button("🔄 CSV zurücksetzen"):
                        st.rerun()
        
        except Exception as e:
            st.error(f"❌ Fehler beim Lesen der CSV-Datei: {str(e)}")
            st.write("Stelle sicher, dass die Datei UTF-8 kodiert ist und das richtige Format hat.")
    
    st.markdown("---")
    
    # Zutaten anzeigen
    st.subheader("Vorhandene Zutaten")
    
    if st.session_state.data["zutaten"]:
        # Gruppiere nach Kategorien
        kategorien = defaultdict(list)
        for name, zutat in st.session_state.data["zutaten"].items():
            kategorien[zutat.get("kategorie", "Sonstiges")].append(name)
        
        for kategorie in sorted(kategorien.keys()):
            with st.expander(f"**{kategorie}** ({len(kategorien[kategorie])} Zutaten)"):
                for zutat_name in sorted(kategorien[kategorie]):
                    zutat = st.session_state.data["zutaten"][zutat_name]
                    
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        st.write(f"**{zutat_name}**")
                        st.write(f"Pro 100g: {zutat['protein']:.1f}g Protein | "
                               f"{zutat['kohlenhydrate']:.1f}g KH | "
                               f"{zutat['fett']:.1f}g Fett | "
                               f"{zutat['kalorien']:.0f} kcal")
                    with col_b:
                        if st.button("🗑️ Löschen", key=f"del_zutat_{zutat_name}"):
                            # Prüfe ob Zutat in Rezepten verwendet wird
                            used_in = [r for r, data in st.session_state.data["rezepte"].items() 
                                      if zutat_name in data["zutaten"]]
                            if used_in:
                                st.error(f"Zutat wird noch in folgenden Rezepten verwendet: {', '.join(used_in)}")
                            else:
                                del st.session_state.data["zutaten"][zutat_name]
                                save_data(st.session_state.data)
                                st.success(f"Zutat '{zutat_name}' gelöscht!")
                                st.rerun()
                    st.markdown("---")
    else:
        st.info("Noch keine Zutaten vorhanden. Füge deine erste Zutat hinzu!")

# TAB 3: REZEPTE
with tab3:
    st.header("Rezepte verwalten")
    
    if not st.session_state.data["zutaten"]:
        st.warning("⚠️ Bitte füge zuerst Zutaten hinzu, bevor du Rezepte erstellst!")
    else:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("Neues Rezept erstellen")
            
            rezept_name = st.text_input("Name des Rezepts", key="rezept_name_input")
            portionen = st.number_input("Anzahl Portionen", min_value=1, value=1, step=1)
            
            st.write("**Zutaten hinzufügen:**")
            
            # Dynamische Zutatenliste
            if 'temp_zutaten' not in st.session_state:
                st.session_state.temp_zutaten = []
            
            col_a, col_b, col_c = st.columns([2, 1, 1])
            with col_a:
                selected_zutat = st.selectbox(
                    "Zutat auswählen",
                    [""] + sorted(st.session_state.data["zutaten"].keys()),
                    key="zutat_select"
                )
            with col_b:
                menge = st.number_input("Menge (g)", min_value=0.0, step=10.0, key="menge_input")
            with col_c:
                st.write("")
                st.write("")
                if st.button("➕ Hinzufügen", key="add_zutat_btn"):
                    if selected_zutat and menge > 0:
                        # Prüfe ob Zutat schon in temporärer Liste
                        existing = next((z for z in st.session_state.temp_zutaten if z[0] == selected_zutat), None)
                        if existing:
                            st.warning(f"'{selected_zutat}' ist bereits in der Liste!")
                        else:
                            st.session_state.temp_zutaten.append((selected_zutat, menge))
                            st.rerun()
            
            # Zeige hinzugefügte Zutaten
            if st.session_state.temp_zutaten:
                st.write("**Aktuelle Zutatenliste:**")
                for idx, (zutat, menge) in enumerate(st.session_state.temp_zutaten):
                    col_x, col_y = st.columns([4, 1])
                    with col_x:
                        st.write(f"- {zutat}: {menge}g")
                    with col_y:
                        if st.button("❌", key=f"remove_temp_zutat_{idx}"):
                            st.session_state.temp_zutaten.pop(idx)
                            st.rerun()
            
            # Rezept speichern
            col_save1, col_save2 = st.columns([1, 3])
            with col_save1:
                if st.button("💾 Rezept speichern", type="primary"):
                    if not rezept_name:
                        st.error("Bitte gib einen Rezeptnamen ein!")
                    elif not st.session_state.temp_zutaten:
                        st.error("Bitte füge mindestens eine Zutat hinzu!")
                    elif rezept_name in st.session_state.data["rezepte"]:
                        st.error(f"Rezept '{rezept_name}' existiert bereits!")
                    else:
                        st.session_state.data["rezepte"][rezept_name] = {
                            "zutaten": {z: m for z, m in st.session_state.temp_zutaten},
                            "portionen": portionen
                        }
                        save_data(st.session_state.data)
                        st.session_state.temp_zutaten = []
                        st.success(f"Rezept '{rezept_name}' erfolgreich gespeichert!")
                        st.rerun()
            with col_save2:
                if st.button("🔄 Zurücksetzen"):
                    st.session_state.temp_zutaten = []
                    st.rerun()
        
        with col2:
            st.subheader("Statistik")
            st.metric("Anzahl Rezepte", len(st.session_state.data["rezepte"]))
            
            # Berechne Nährwerte für temporäres Rezept
            if st.session_state.temp_zutaten:
                st.write("**Vorschau Nährwerte:**")
                temp_rezept = {
                    "zutaten": {z: m for z, m in st.session_state.temp_zutaten},
                    "portionen": portionen
                }
                nutrition = calculate_recipe_nutrition(temp_rezept, st.session_state.data["zutaten"])
                
                st.write(f"**Gesamt:**")
                st.write(f"- {nutrition['kalorien']:.0f} kcal")
                st.write(f"- {nutrition['protein']:.1f}g Protein")
                st.write(f"- {nutrition['kohlenhydrate']:.1f}g KH")
                st.write(f"- {nutrition['fett']:.1f}g Fett")
                
                if portionen > 1:
                    st.write(f"**Pro Portion ({portionen} Portionen):**")
                    st.write(f"- {nutrition['kalorien']/portionen:.0f} kcal")
                    st.write(f"- {nutrition['protein']/portionen:.1f}g Protein")
                    st.write(f"- {nutrition['kohlenhydrate']/portionen:.1f}g KH")
                    st.write(f"- {nutrition['fett']/portionen:.1f}g Fett")
        
        st.markdown("---")
        
        # Vorhandene Rezepte anzeigen
        st.subheader("Vorhandene Rezepte")
        
        if st.session_state.data["rezepte"]:
            for rezept_name, rezept in st.session_state.data["rezepte"].items():
                with st.expander(f"**{rezept_name}** ({rezept['portionen']} Portion{'en' if rezept['portionen'] > 1 else ''})"):
                    col_a, col_b = st.columns([2, 1])
                    
                    with col_a:
                        st.write("**Zutaten:**")
                        for zutat, menge in rezept["zutaten"].items():
                            if zutat in st.session_state.data["zutaten"]:
                                st.write(f"- {zutat}: {menge}g")
                            else:
                                st.write(f"- {zutat}: {menge}g ⚠️ (Zutat nicht mehr vorhanden)")
                    
                    with col_b:
                        nutrition = calculate_recipe_nutrition(rezept, st.session_state.data["zutaten"])
                        st.write("**Nährwerte (gesamt):**")
                        st.write(f"- {nutrition['kalorien']:.0f} kcal")
                        st.write(f"- {nutrition['protein']:.1f}g Protein")
                        st.write(f"- {nutrition['kohlenhydrate']:.1f}g KH")
                        st.write(f"- {nutrition['fett']:.1f}g Fett")
                        
                        if rezept['portionen'] > 1:
                            st.write(f"**Pro Portion:**")
                            st.write(f"- {nutrition['kalorien']/rezept['portionen']:.0f} kcal")
                            st.write(f"- {nutrition['protein']/rezept['portionen']:.1f}g Protein")
                    
                    if st.button("🗑️ Rezept löschen", key=f"del_rezept_{rezept_name}"):
                        # Prüfe ob Rezept im Wochenplan verwendet wird
                        used_in_plan = []
                        for tag, mahlzeiten in st.session_state.data["wochenplan"].items():
                            for mahlzeit in mahlzeiten:
                                if mahlzeit.get("rezept") == rezept_name:
                                    used_in_plan.append(f"{tag} ({mahlzeit['zeit']} Uhr)")
                        
                        if used_in_plan:
                            st.error(f"Rezept wird noch im Wochenplan verwendet: {', '.join(used_in_plan)}")
                        else:
                            del st.session_state.data["rezepte"][rezept_name]
                            save_data(st.session_state.data)
                            st.success(f"Rezept '{rezept_name}' gelöscht!")
                            st.rerun()
        else:
            st.info("Noch keine Rezepte vorhanden. Erstelle dein erstes Rezept!")

# TAB 4: WOCHENPLAN
with tab4:
    st.header("Wochenplan zusammenstellen")
    
    if not st.session_state.data["rezepte"]:
        st.warning("⚠️ Bitte erstelle zuerst Rezepte, bevor du deinen Wochenplan erstellst!")
    else:
        # Wähle Tag aus
        selected_day = st.selectbox(
            "Wähle einen Tag",
            ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"],
            key="day_selector"
        )
        
        st.markdown("---")
        
        # Zeige Mahlzeiten für ausgewählten Tag
        st.subheader(f"Mahlzeiten für {selected_day}")
        
        mahlzeiten = st.session_state.data["wochenplan"][selected_day]
        
        # Sortiere nach Zeit
        mahlzeiten.sort(key=lambda x: x["zeit"])
        
        # Zeige vorhandene Mahlzeiten
        if mahlzeiten:
            for idx, mahlzeit in enumerate(mahlzeiten):
                col1, col2, col3 = st.columns([1, 3, 1])
                
                with col1:
                    st.write(f"**{mahlzeit['zeit']} Uhr**")
                
                with col2:
                    rezept_name = mahlzeit["rezept"]
                    st.write(f"**{rezept_name}**")
                    
                    # Zeige Nährwerte
                    if rezept_name in st.session_state.data["rezepte"]:
                        nutrition = calculate_recipe_nutrition(
                            st.session_state.data["rezepte"][rezept_name],
                            st.session_state.data["zutaten"]
                        )
                        portionen = st.session_state.data["rezepte"][rezept_name]["portionen"]
                        
                        if portionen > 1:
                            st.caption(f"Pro Portion: {nutrition['kalorien']/portionen:.0f} kcal | "
                                     f"{nutrition['protein']/portionen:.1f}g P | "
                                     f"{nutrition['kohlenhydrate']/portionen:.1f}g KH | "
                                     f"{nutrition['fett']/portionen:.1f}g F")
                        else:
                            st.caption(f"{nutrition['kalorien']:.0f} kcal | "
                                     f"{nutrition['protein']:.1f}g P | "
                                     f"{nutrition['kohlenhydrate']:.1f}g KH | "
                                     f"{nutrition['fett']:.1f}g F")
                
                with col3:
                    if st.button("🗑️", key=f"del_{selected_day}_{idx}", help="Mahlzeit löschen"):
                        st.session_state.data["wochenplan"][selected_day].pop(idx)
                        save_data(st.session_state.data)
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info(f"Noch keine Mahlzeiten für {selected_day} geplant.")
        
        # Neue Mahlzeit hinzufügen
        st.subheader("➕ Neue Mahlzeit hinzufügen")
        
        col_a, col_b, col_c = st.columns([1, 2, 1])
        
        with col_a:
            # Zeit-Eingabe
            neue_zeit = st.time_input(
                "Uhrzeit",
                value=None,
                key=f"time_input_{selected_day}"
            )
        
        with col_b:
            # Rezept-Auswahl
            rezept_optionen = sorted(st.session_state.data["rezepte"].keys())
            neues_rezept = st.selectbox(
                "Rezept",
                [""] + rezept_optionen,
                key=f"rezept_select_{selected_day}"
            )
        
        with col_c:
            st.write("")
            st.write("")
            if st.button("✅ Hinzufügen", type="primary", key=f"add_meal_{selected_day}"):
                if not neue_zeit:
                    st.error("Bitte wähle eine Uhrzeit!")
                elif not neues_rezept:
                    st.error("Bitte wähle ein Rezept!")
                else:
                    # Formatiere Zeit als String
                    zeit_str = neue_zeit.strftime("%H:%M")
                    
                    # Füge Mahlzeit hinzu
                    st.session_state.data["wochenplan"][selected_day].append({
                        "zeit": zeit_str,
                        "rezept": neues_rezept
                    })
                    
                    # Sortiere nach Zeit
                    st.session_state.data["wochenplan"][selected_day].sort(key=lambda x: x["zeit"])
                    
                    save_data(st.session_state.data)
                    st.success(f"Mahlzeit um {zeit_str} Uhr hinzugefügt!")
                    st.rerun()
        
        st.markdown("---")
        
        # Wochenübersicht
        st.subheader("📅 Wochenübersicht")
        
        for tag in ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]:
            mahlzeiten_tag = st.session_state.data["wochenplan"][tag]
            
            if mahlzeiten_tag:
                with st.expander(f"**{tag}** ({len(mahlzeiten_tag)} Mahlzeit{'en' if len(mahlzeiten_tag) != 1 else ''})"):
                    for mahlzeit in sorted(mahlzeiten_tag, key=lambda x: x["zeit"]):
                        col_x, col_y = st.columns([1, 3])
                        with col_x:
                            st.write(f"**{mahlzeit['zeit']}**")
                        with col_y:
                            st.write(mahlzeit['rezept'])
        
        st.markdown("---")
        
        # Button zum Zurücksetzen
        col_reset1, col_reset2, col_reset3 = st.columns([1, 2, 1])
        with col_reset1:
            if st.button(f"🔄 {selected_day} leeren", type="secondary"):
                st.session_state.data["wochenplan"][selected_day] = []
                save_data(st.session_state.data)
                st.success(f"{selected_day} wurde geleert!")
                st.rerun()
        
        with col_reset3:
            if st.button("🗑️ Ganze Woche leeren", type="secondary"):
                for tag in st.session_state.data["wochenplan"]:
                    st.session_state.data["wochenplan"][tag] = []
                save_data(st.session_state.data)
                st.success("Wochenplan komplett zurückgesetzt!")
                st.rerun()

# TAB 5: EINKAUFSLISTE
with tab5:
    st.header("Einkaufsliste")
    
    einkaufsliste = generate_shopping_list(st.session_state.data)
    
    if not einkaufsliste:
        st.info("Dein Wochenplan ist leer. Füge Rezepte hinzu, um eine Einkaufsliste zu erstellen!")
    else:
        st.success(f"✅ Einkaufsliste für {len(einkaufsliste)} verschiedene Zutaten generiert!")
        
        # Gruppiere nach Kategorien
        kategorisierte_liste = defaultdict(list)
        for zutat_name, menge in sorted(einkaufsliste.items()):
            if zutat_name in st.session_state.data["zutaten"]:
                kategorie = st.session_state.data["zutaten"][zutat_name].get("kategorie", "Sonstiges")
            else:
                kategorie = "Unbekannt"
            kategorisierte_liste[kategorie].append((zutat_name, menge))
        
        # Zeige nach Kategorien sortiert
        for kategorie in sorted(kategorisierte_liste.keys()):
            st.subheader(kategorie)
            for zutat_name, menge in kategorisierte_liste[kategorie]:
                # Runde auf sinnvolle Werte
                if menge >= 1000:
                    st.write(f"☐ **{zutat_name}**: {menge/1000:.2f} kg")
                else:
                    st.write(f"☐ **{zutat_name}**: {menge:.0f} g")
            st.markdown("---")
        
        # Export-Optionen
        st.subheader("Export")
        
        # Textformat für Clipboard
        text_liste = "EINKAUFSLISTE\n" + "="*50 + "\n\n"
        for kategorie in sorted(kategorisierte_liste.keys()):
            text_liste += f"{kategorie.upper()}\n" + "-"*30 + "\n"
            for zutat_name, menge in kategorisierte_liste[kategorie]:
                if menge >= 1000:
                    text_liste += f"☐ {zutat_name}: {menge/1000:.2f} kg\n"
                else:
                    text_liste += f"☐ {zutat_name}: {menge:.0f} g\n"
            text_liste += "\n"
        
        text_liste += f"\nErstellt am: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
        
        st.text_area("Kopiere diese Liste:", text_liste, height=300)
        
        st.caption("💡 Tipp: Kopiere den Text und füge ihn in eine Notiz-App auf deinem Smartphone ein!")

# Footer
st.markdown("---")
st.caption("Ernährungsplaner v1.0 | Erstellt mit Streamlit")
