import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder

# Configuration de la page
st.set_page_config(
    page_title="Analyse Performance Chevaux 2025",
    page_icon="🐴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialiser les variables de session
if 'victoire_count' not in st.session_state:
    st.session_state.victoire_count = 0

# CSS personnalisé
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    [data-testid="metric-container"] [data-testid="metric-label"] {
        font-size: 12px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Titre
st.markdown("#  Analyse conditions par Handicap")
st.markdown("---")

# Charger les données
@st.cache_data
def load_data():
    df = pd.read_excel('Performance_all4.xlsx')
    return df

@st.cache_data
def load_codification():
    df_codif = pd.read_excel('CODIFICATION_2025.xlsx')
    return df_codif

df = load_data()
df_codification = load_codification()

# Convertir DATE_COURSE en datetime
df['DATE_COURSE'] = pd.to_datetime(df['DATE_COURSE'])

# Obtenir les dates min et max du dataset brut
date_min_global = df['DATE_COURSE'].min()
date_max_global = df['DATE_COURSE'].max()

# Sidebar - Filtres
st.sidebar.markdown("## ⚙️ Filtres")

# Filtre de date
st.sidebar.markdown("### 📅 Période de Course")

# Bouton pour sélectionner l'année 2025
col_btn, col_range = st.sidebar.columns([1, 2])
with col_btn:
    if st.button("📅 2025", use_container_width=True):
        st.session_state.date_range = (
            datetime(2025, 1, 1).date(),
            datetime(2025, 12, 31).date()
        )
        st.rerun()

# Initialiser session state si nécessaire
if 'date_range' not in st.session_state:
    st.session_state.date_range = (date_min_global.date(), date_max_global.date())

# Filtre de plage de dates
date_range = st.sidebar.date_input(
    "Sélectionner la plage de dates:",
    value=st.session_state.date_range,
    min_value=date_min_global.date(),
    max_value=date_max_global.date(),
    format="DD/MM/YYYY"
)

# Vérifier si date_range contient deux dates
if len(date_range) == 2:
    date_start, date_end = date_range
    st.session_state.date_range = (date_start, date_end)
else:
    date_start = date_range[0] if len(date_range) > 0 else st.session_state.date_range[0]
    date_end = st.session_state.date_range[1]

# Filtrer les données par date AVANT le groupby (comme la requête SQL)
df_filtered_by_date = df[
    (df['DATE_COURSE'].dt.date >= date_start) &
    (df['DATE_COURSE'].dt.date <= date_end)
].copy()

# Placeholder pour afficher le range (sera mis à jour après les filtres)
range_display = st.sidebar.empty()



# Préparer les données groupées APRÈS filtrage par date
df_clean = df_filtered_by_date.copy()
df_grouped = df_clean.groupby('ID_CHEVAL').agg({
    'VALEUR_CHEVAL': 'first',
    'NOMBRE_VICTOIRE': 'sum',  # Somme totale des victoires sur la période
    'NOMBRE_COURSE': 'sum',     # Somme totale des courses
    'NOMBRE_PLACE': 'sum',      # Somme totale des places
    'JOCKEY': 'first',
    'PROPRIETAIRE': 'first',
    'ENTRAINEUR': 'first',
    'CODE_RACE_CHEVAL': 'first',
    'CODE_ORIGINE_CHEVAL': 'first',
    'CODE_NATURE_COURSE': 'first',
    'CODE_CATEGORIE_COURSE': 'first',
    'CODE_CATEGORISATION_COURSE': 'first',
    'CODE_AGE_CHEVAL': 'first',
    'AGE': 'first',  # Ajouter la colonne AGE
    'DATE_COURSE': 'min',
    'ALLOCATION_VICTOIRE': 'sum',  # Somme totale des allocations victoire
    'ALLOCATION_PLACE': 'sum'       # Somme totale des allocations place
}).reset_index()

# Remplacer les valeurs vides par 'I' pour CODE_ORIGINE_CHEVAL
df_grouped['CODE_ORIGINE_CHEVAL'] = df_grouped['CODE_ORIGINE_CHEVAL'].fillna('I')

# Remplacer les valeurs vides par 'NA' pour CODE_CATEGORISATION_COURSE (986 NaN)
df_grouped['CODE_CATEGORISATION_COURSE'] = df_grouped['CODE_CATEGORISATION_COURSE'].fillna('NA')

# Fonction pour appliquer la logique de filtre d'âge
def apply_age_filter(selected_ages, df_filtered_data):
    """
    Applique la logique de filtre d'âge:
    - '2' → AGE == 2
    - '3' → AGE == 3
    - '3+' → AGE >= 3
    - '4' → AGE == 4
    - '4+' → AGE >= 4
    - '5+' → AGE >= 5
    """
    if not selected_ages:
        return df_filtered_data.copy()
    
    mask = pd.Series([False] * len(df_filtered_data), index=df_filtered_data.index)
    
    for age_code in selected_ages:
        if age_code == '2':
            mask |= (df_filtered_data['AGE'] == 2)
        elif age_code == '3':
            mask |= (df_filtered_data['AGE'] == 3)
        elif age_code == '3+':
            mask |= (df_filtered_data['AGE'] >= 3)
        elif age_code == '4':
            mask |= (df_filtered_data['AGE'] == 4)
        elif age_code == '4+':
            mask |= (df_filtered_data['AGE'] >= 4)
        elif age_code == '5+':
            mask |= (df_filtered_data['AGE'] >= 5)
    
    return mask

st.sidebar.markdown("---")

# Filtres numériques
st.sidebar.markdown("### 🏆 Nombre de Victoires")

victoire_min, victoire_max = st.sidebar.slider(
    "Plage de victoires",
    min_value=0,
    max_value=int(df_grouped['NOMBRE_VICTOIRE'].max()),
    value=(0, int(df_grouped['NOMBRE_VICTOIRE'].max())),
    step=1,
    label_visibility="collapsed"
)

st.sidebar.markdown("### 💰 Allocation Victoire")
col_av1, col_av2 = st.sidebar.columns(2)
with col_av1:
    allocation_victoire_min = st.number_input(
        ">= Min",
        min_value=int(df_grouped['ALLOCATION_VICTOIRE'].min()),
        max_value=int(df_grouped['ALLOCATION_VICTOIRE'].max()),
        value=int(df_grouped['ALLOCATION_VICTOIRE'].min()),
        step=1,
        key="alloc_vic_min"
    )
with col_av2:
    allocation_victoire_max = st.number_input(
        "<= Max",
        min_value=int(df_grouped['ALLOCATION_VICTOIRE'].min()),
        max_value=int(df_grouped['ALLOCATION_VICTOIRE'].max()),
        value=int(df_grouped['ALLOCATION_VICTOIRE'].max()),
        step=1,
        key="alloc_vic_max"
    )

st.sidebar.markdown("### 🏅 Allocation Place")
col_ap1, col_ap2 = st.sidebar.columns(2)
with col_ap1:
    allocation_place_min = st.number_input(
        ">= Min",
        min_value=int(df_grouped['ALLOCATION_PLACE'].min()),
        max_value=int(df_grouped['ALLOCATION_PLACE'].max()),
        value=int(df_grouped['ALLOCATION_PLACE'].min()),
        step=1,
        key="alloc_place_min"
    )
with col_ap2:
    allocation_place_max = st.number_input(
        "<= Max",
        min_value=int(df_grouped['ALLOCATION_PLACE'].min()),
        max_value=int(df_grouped['ALLOCATION_PLACE'].max()),
        value=int(df_grouped['ALLOCATION_PLACE'].max()),
        step=1,
        key="alloc_place_max"
    )

# Filtres catégoriques
st.sidebar.markdown("### 🏷️ Critères de Race/Origine")

code_age_options = sorted(df_grouped['CODE_AGE_CHEVAL'].dropna().unique())
code_age_selected = st.sidebar.multiselect(
    "Code Age Cheval:",
    options=code_age_options,
    default=code_age_options
)

code_race_options = sorted(df_grouped['CODE_RACE_CHEVAL'].dropna().unique())
code_race_default = [x for x in ['AA2A5', 'A2575', 'PSA', 'PSAN'] if x in code_race_options]
code_race_selected = st.sidebar.multiselect(
    "Code Race Cheval:",
    options=code_race_options,
    default=code_race_default
)

code_origine_options = sorted(df_grouped['CODE_ORIGINE_CHEVAL'].unique())
code_origine_selected = st.sidebar.multiselect(
    "Code Origine Cheval:",
    options=code_origine_options,
    default=code_origine_options
)

st.sidebar.markdown("###  Critères de Course")
code_nature_options = sorted(df_grouped['CODE_NATURE_COURSE'].dropna().unique())
code_nature_default = [x for x in ['CODIF'] if x in code_nature_options]
code_nature_selected = st.sidebar.multiselect(
    "Code Nature Course:",
    options=code_nature_options,
    default=code_nature_default
)

code_categorie_options = sorted(df_grouped['CODE_CATEGORIE_COURSE'].dropna().unique())
code_categorie_selected = st.sidebar.multiselect(
    "Code Catégorie Course:",
    options=code_categorie_options,
    default=code_categorie_options
)

code_categorisation_options = sorted(df_grouped['CODE_CATEGORISATION_COURSE'].dropna().unique())
code_categorisation_default = [x for x in ['A', 'B', 'C', 'D', 'E'] if x in code_categorisation_options]
code_categorisation_selected = st.sidebar.multiselect(
    "Code Catégorisation Course:",
    options=code_categorisation_options,
    default=code_categorisation_default
)

# Appliquer le filtre d'âge avec la logique conditionnelle
age_mask = apply_age_filter(code_age_selected, df_grouped)

# Appliquer tous les filtres
df_filtered = df_grouped[
    (df_grouped['NOMBRE_VICTOIRE'] >= victoire_min) &
    (df_grouped['NOMBRE_VICTOIRE'] <= victoire_max) &
    (df_grouped['ALLOCATION_VICTOIRE'] >= allocation_victoire_min) &
    (df_grouped['ALLOCATION_VICTOIRE'] <= allocation_victoire_max) &
    (df_grouped['ALLOCATION_PLACE'] >= allocation_place_min) &
    (df_grouped['ALLOCATION_PLACE'] <= allocation_place_max) &
    age_mask &
    (df_grouped['CODE_AGE_CHEVAL'].isin(code_age_selected)) &
    (df_grouped['CODE_RACE_CHEVAL'].isin(code_race_selected)) &
    (df_grouped['CODE_ORIGINE_CHEVAL'].isin(code_origine_selected)) &
    (df_grouped['CODE_NATURE_COURSE'].isin(code_nature_selected)) &
    (df_grouped['CODE_CATEGORIE_COURSE'].isin(code_categorie_selected)) &
    (df_grouped['CODE_CATEGORISATION_COURSE'].isin(code_categorisation_selected))
].copy()

# Afficher le range des dates basé sur les chevaux réellement filtrés
filtered_horse_ids = set(df_filtered['ID_CHEVAL'].values)
df_filtered_by_horse = df_filtered_by_date[df_filtered_by_date['ID_CHEVAL'].isin(filtered_horse_ids)]
if len(df_filtered_by_horse) > 0:
    actual_min_date = df_filtered_by_horse['DATE_COURSE'].min()
    actual_max_date = df_filtered_by_horse['DATE_COURSE'].max()
    range_display.markdown(f"**📍 Range:** {actual_min_date.strftime('%d/%m/%Y')} → {actual_max_date.strftime('%d/%m/%Y')}")
else:
    range_display.markdown(f"**📍 Range:** Aucune donnée")

# Statistiques principales
st.markdown("## 📊 Statistiques Principales")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    # Compter le nombre total de ID_CHEVAL DISTINCT filtrés
    nombre_chevaux_distinct = len(df_filtered)
    st.metric(
        label="Nombre de Chevaux",
        value=f"{nombre_chevaux_distinct:,}"
    )

with col2:
    st.metric(
        label="Valeur Moyenne",
        value=f"{df_filtered['VALEUR_CHEVAL'].mean():,.0f}",
        delta=f"Min: {df_filtered['VALEUR_CHEVAL'].min():,.0f}"
    )

with col3:
    st.metric(
        label="Valeur Médiane",
        value=f"{df_filtered['VALEUR_CHEVAL'].median():,.0f}",
        delta=f"Max: {df_filtered['VALEUR_CHEVAL'].max():,.0f}"
    )

with col4:
    st.metric(
        label="Victoires Moyennes",
        value=f"{df_filtered['NOMBRE_VICTOIRE'].mean():.1f}",
        delta=f"Écart-type: {df_filtered['NOMBRE_VICTOIRE'].std():.1f}"
    )

with col5:
    st.metric(
        label="Courses Moyennes",
        value=f"{df_filtered['NOMBRE_COURSE'].mean():.1f}",
        delta=f"Max: {df_filtered['NOMBRE_COURSE'].max():.0f}"
    )

st.markdown("---")

# Section Analyse Courses/Conditions - Nouvelle Section
st.markdown("## 🏇 Analyse par Course (Conditions et Engagements)")

# Préparer les données pour la jointure avec CODIFICATION
if 'ID_COURSE' in df_filtered_by_date.columns:
    # Joindre les données filtrées par date avec la codification
    df_courses_data = df_filtered_by_date[['ID_CHEVAL', 'ID_COURSE', 'DATE_COURSE']].drop_duplicates().copy()
    
    # Joindre avec CODIFICATION sur ID_COURSE
    df_courses_merged = df_courses_data.merge(
        df_codification[['ID_COURSE', 'NOM_PRIX', 'ID_CONDITION', 'NBR_ENGAGEMENT', 'NBR_PARTANT']],
        on='ID_COURSE',
        how='left'
    )
    
    # Filtrer pour garder seulement les chevaux présents dans df_filtered
    filtered_horse_ids = set(df_filtered['ID_CHEVAL'].values)
    df_courses_merged = df_courses_merged[df_courses_merged['ID_CHEVAL'].isin(filtered_horse_ids)]
    
    if len(df_courses_merged) > 0:
        # Créer des statistiques aggées par course
        df_course_stats = df_courses_merged.groupby(['ID_COURSE', 'NOM_PRIX', 'ID_CONDITION']).agg({
            'NBR_ENGAGEMENT': 'first',
            'NBR_PARTANT': 'first',
            'ID_CHEVAL': 'count',
            'DATE_COURSE': 'first'
        }).reset_index().rename(columns={'ID_CHEVAL': 'Chevaux Filtrés'})
        
        df_course_stats = df_course_stats.sort_values('DATE_COURSE', ascending=False)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"📍 {len(df_course_stats)} courses trouvées pour les chevaux filtrés")
            
        with col2:
            st.info(f"📊 Engagements moyens: {df_course_stats['NBR_ENGAGEMENT'].mean():.1f} | Partants moyens: {df_course_stats['NBR_PARTANT'].mean():.1f}")
        
        # Afficher le tableau détaillé
        st.markdown("### 📋 Détail des Courses")
        
        df_display = df_course_stats[[
            'ID_COURSE', 'NOM_PRIX', 'ID_CONDITION', 'NBR_ENGAGEMENT', 'NBR_PARTANT', 'Chevaux Filtrés', 'DATE_COURSE'
        ]].copy()
        
        df_display.columns = ['ID Course', 'Nom Prix', 'Condition', 'Engagements', 'Partants', 'Chevaux Filtrés', 'Date']
        df_display['Date'] = df_display['Date'].dt.strftime('%d/%m/%Y')
        
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True
        )
        
        # Graphiques d'analyse
        col1, col2 = st.columns(2)
        
        with col1:
            # Distribution des engagements
            fig_eng = px.histogram(
                df_course_stats,
                x='NBR_ENGAGEMENT',
                nbins=20,
                title='Distribution Nombre d\'Engagements',
                labels={'NBR_ENGAGEMENT': 'Nombre Engagements', 'count': 'Nombre de Courses'},
                color_discrete_sequence=['#636EFA']
            )
            fig_eng.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_eng, use_container_width=True)
        
        with col2:
            # Distribution des partants
            fig_part = px.histogram(
                df_course_stats,
                x='NBR_PARTANT',
                nbins=20,
                title='Distribution Nombre de Partants',
                labels={'NBR_PARTANT': 'Nombre Partants', 'count': 'Nombre de Courses'},
                color_discrete_sequence=['#EF553B']
            )
            fig_part.update_layout(height=350, showlegend=False)
            st.plotly_chart(fig_part, use_container_width=True)
        
    else:
        st.warning("⚠️ Aucune donnée de course disponible pour les chevaux filtrés.")
else:
    st.warning("⚠️ La colonne ID_COURSE n'a pas été trouvée dans les données.")

st.markdown("---")

# Section 1: Distribution de la valeur
st.markdown("## 📈 Distribution de la Valeur des Chevaux")
col1, col2 = st.columns(2)

with col1:
    # Histogramme
    fig_hist = px.histogram(
        df_filtered,
        x='VALEUR_CHEVAL',
        nbins=40,
        title='Histogramme de Distribution',
        labels={'VALEUR_CHEVAL': 'Valeur', 'count': 'Nombre de chevaux'},
        color_discrete_sequence=['#1f77b4']
    )
    fig_hist.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig_hist, use_container_width=True)

with col2:
    # Box plot
    fig_box = px.box(
        df_filtered,
        y='VALEUR_CHEVAL',
        title='Box Plot de la Valeur',
        labels={'VALEUR_CHEVAL': 'Valeur'},
        color_discrete_sequence=['#ff7f0e']
    )
    fig_box.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

st.markdown("---")

# Section 2: Relation Valeur vs Victoires
st.markdown("## 🏆 Analyse Valeur vs Nombre de Victoires")
col1, col2 = st.columns(2)

with col1:
    # Scatter plot
    fig_scatter = px.scatter(
        df_filtered,
        x='NOMBRE_VICTOIRE',
        y='VALEUR_CHEVAL',
        size='NOMBRE_COURSE',
        color='NOMBRE_VICTOIRE',
        title='Valeur vs Victoires (taille = courses)',
        labels={
            'NOMBRE_VICTOIRE': 'Nombre de Victoires',
            'VALEUR_CHEVAL': 'Valeur '
        },
        color_continuous_scale='Viridis',
        hover_data={
            'NOMBRE_VICTOIRE': True,
            'VALEUR_CHEVAL': ':.0f',
            'NOMBRE_COURSE': True
        }
    )
    fig_scatter.update_layout(height=450)
    st.plotly_chart(fig_scatter, use_container_width=True)

with col2:
    # Corrélation
    correlation = df_filtered['NOMBRE_VICTOIRE'].corr(df_filtered['VALEUR_CHEVAL'])
    
    fig_line = px.line(
        df_filtered.sort_values('NOMBRE_VICTOIRE'),
        x='NOMBRE_VICTOIRE',
        y='VALEUR_CHEVAL',
        title='Tendance Valeur vs Victoires',
        labels={
            'NOMBRE_VICTOIRE': 'Nombre de Victoires',
            'VALEUR_CHEVAL': 'Valeur'
        },
        color_discrete_sequence=['#2ca02c']
    )
    fig_line.add_scatter(
        x=df_filtered['NOMBRE_VICTOIRE'],
        y=df_filtered['VALEUR_CHEVAL'],
        mode='markers',
        marker=dict(size=5, opacity=0.5),
        showlegend=False
    )
    fig_line.update_layout(height=450)
    st.plotly_chart(fig_line, use_container_width=True)

st.info(f"📌 **Corrélation** entre victoires et valeur: {correlation:.3f}")

st.markdown("---")

# Section 2bis: Relation Valeur vs Code Catégorisation Course
st.markdown("##  Analyse Valeur vs Code Catégorisation Course")
col1, col2 = st.columns(2)

with col1:
    # Box plot: Valeur par CODE_CATEGORISATION_COURSE
    fig_box_cat = px.box(
        df_filtered,
        x='CODE_CATEGORISATION_COURSE',
        y='VALEUR_CHEVAL',
        title='Distribution Valeur par Catégorisation Course',
        labels={
            'CODE_CATEGORISATION_COURSE': 'Code Catégorisation',
            'VALEUR_CHEVAL': 'Valeur'
        },
        color='CODE_CATEGORISATION_COURSE',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_box_cat.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig_box_cat, use_container_width=True)

with col2:
    # Barplot: Nombre de chevaux et valeur moyenne par CODE_CATEGORISATION_COURSE
    df_cat_stats = df_filtered.groupby('CODE_CATEGORISATION_COURSE').agg({
        'ID_CHEVAL': 'count',
        'VALEUR_CHEVAL': 'mean'
    }).reset_index().rename(columns={'ID_CHEVAL': 'Nombre de chevaux', 'VALEUR_CHEVAL': 'Valeur moyenne'})
    
    fig_bar_cat = px.bar(
        df_cat_stats,
        x='CODE_CATEGORISATION_COURSE',
        y='Valeur moyenne',
        title='Valeur Moyenne par Catégorisation',
        labels={'CODE_CATEGORISATION_COURSE': 'Code Catégorisation'},
        color='Valeur moyenne',
        color_continuous_scale='Viridis',
        text='Valeur moyenne'
    )
    fig_bar_cat.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig_bar_cat.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig_bar_cat, use_container_width=True)

st.markdown("---")

# Section 2ter: Tableau détaillé Catégorisation vs Valeur vs Nombre Chevaux
st.markdown("##  Analyse Valeur et Code Catégorisation Course et Nombre Chevaux")

# Créer un tableau détaillé
table_cat_detail = df_filtered.groupby('CODE_CATEGORISATION_COURSE').agg({
    'ID_CHEVAL': 'count',
    'VALEUR_CHEVAL': ['mean', 'median', 'min', 'max', 'std']
}).reset_index()

table_cat_detail.columns = ['Code Catégorisation', 'Nombre Chevaux', 'Valeur Moyenne', 'Valeur Médiane', 'Valeur Min', 'Valeur Max', 'Écart-type']

# Formater les valeurs
for col in ['Valeur Moyenne', 'Valeur Médiane', 'Valeur Min', 'Valeur Max', 'Écart-type']:
    table_cat_detail[col] = table_cat_detail[col].apply(lambda x: f"{x:,.0f}")

# Afficher le tableau
st.dataframe(
    table_cat_detail,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# Section 2ter-bis: Tableau croisé Catégorisation vs Ranges de Valeur
st.markdown("## Analyse Catégorisation Course vs Ranges de Valeur vs Nombre Chevaux")

# Créer les ranges de valeur pour cette analyse
df_filtered_temp = df_filtered.copy()
df_filtered_temp['PLAGE_VALEUR_DETAIL'] = pd.cut(
    df_filtered_temp['VALEUR_CHEVAL'],
    bins=[0, 18, 24, 30, 34, float('inf')],
    labels=['[0,18]', ']18,24]', ']24,30]', ']30,34]', '34+'],
    include_lowest=True
)

# Créer un tableau croisé
table_cat_valeur = df_filtered_temp.groupby(['CODE_CATEGORISATION_COURSE', 'PLAGE_VALEUR_DETAIL']).agg({
    'ID_CHEVAL': 'count',
    'VALEUR_CHEVAL': 'mean'
}).reset_index()

table_cat_valeur.columns = ['Code Catégorisation', 'Plage Valeur', 'Nombre Chevaux', 'Valeur Moyenne']

# Formater la valeur moyenne
table_cat_valeur['Valeur Moyenne'] = table_cat_valeur['Valeur Moyenne'].apply(lambda x: f"{x:,.0f}")

# Afficher le tableau
st.dataframe(
    table_cat_valeur,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")
st.markdown("## 📦 Distribution par Plages de Victoires")

df_filtered['PLAGE_VICTOIRES'] = pd.cut(
    df_filtered['NOMBRE_VICTOIRE'],
    bins=[-1, 5, 10, 15, 20, 100],
    labels=['0-5', '6-10', '11-15', '16-20', '20+'],
    include_lowest=True
)

col1, col2 = st.columns(2)

with col1:
    fig_box_range = px.box(
        df_filtered,
        x='PLAGE_VICTOIRES',
        y='VALEUR_CHEVAL',
        title='Valeur par Plage de Victoires',
        labels={'PLAGE_VICTOIRES': 'Plage de Victoires', 'VALEUR_CHEVAL': 'Valeur'},
        color='PLAGE_VICTOIRES',
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig_box_range.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig_box_range, use_container_width=True)

with col2:
    fig_bar = px.bar(
        df_filtered.groupby('PLAGE_VICTOIRES').agg({
            'ID_CHEVAL': 'count',
            'VALEUR_CHEVAL': 'mean'
        }).reset_index().rename(columns={'ID_CHEVAL': 'Nombre de chevaux', 'VALEUR_CHEVAL': 'Valeur moyenne'}),
        x='PLAGE_VICTOIRES',
        y=['Nombre de chevaux'],
        title='Nombre de Chevaux par Plage',
        labels={'PLAGE_VICTOIRES': 'Plage de Victoires'},
        color_discrete_sequence=['#d62728']
    )
    fig_bar.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# Section 4: Tableau détaillé
st.markdown("## 📋 Top 10 Chevaux par Valeur")
top_chevaux = df_filtered.nlargest(10, 'VALEUR_CHEVAL')[
    ['ID_CHEVAL', 'VALEUR_CHEVAL', 'NOMBRE_VICTOIRE', 'NOMBRE_COURSE', 'NOMBRE_PLACE', 'JOCKEY', 'PROPRIETAIRE']
].copy()

top_chevaux.columns = ['ID Cheval', 'Valeur', 'Victoires', 'Courses', 'Places', 'Jockey', 'Propriétaire']
top_chevaux['Valeur'] = top_chevaux['Valeur'].apply(lambda x: f"{x:,.0f}")

st.dataframe(
    top_chevaux,
    use_container_width=True,
    hide_index=True
)

st.markdown("---")

# Section 5: Distribution d'Âge des Chevaux
st.markdown("##  Distribution d'Âge des Chevaux")

col1, col2 = st.columns(2)

with col1:
    # Graphique de distribution d'âge global
    age_count = df_filtered.groupby('AGE', dropna=False).agg({'ID_CHEVAL': 'count'}).reset_index()
    age_count.columns = ['AGE', 'Nombre']
    age_count = age_count.sort_values('AGE')
    
    fig_age_dist = px.bar(
        age_count,
        x='AGE',
        y='Nombre',
        title='Distribution des Chevaux par Âge',
        labels={'AGE': 'Âge', 'Nombre': 'Nombre de Chevaux'},
        color='Nombre',
        color_continuous_scale='Viridis'
    )
    fig_age_dist.update_layout(height=450, showlegend=False)
    st.plotly_chart(fig_age_dist, use_container_width=True)

with col2:
    # Graphique en barres empilées: Age par Race
    age_race_data = df_filtered.groupby(['CODE_RACE_CHEVAL', 'AGE']).agg({'ID_CHEVAL': 'count'}).reset_index()
    age_race_data.columns = ['Race', 'Âge', 'Nombre']
    
    fig_age_race = px.bar(
        age_race_data,
        x='Race',
        y='Nombre',
        color='Âge',
        title='Distribution d\'Âge par Race',
        labels={'Race': 'Race', 'Nombre': 'Nombre de Chevaux', 'Âge': 'Âge'},
        barmode='stack',
        color_continuous_scale='Viridis'
    )
    fig_age_race.update_layout(height=450)
    st.plotly_chart(fig_age_race, use_container_width=True)

st.markdown("---")

# Nouveau tableau: Distribution par Ranges de Valeur et Critères
st.markdown("##  Distribution par Ranges de Valeur (Race, Âge, Origine)")

# Créer les ranges de valeur
df_filtered['PLAGE_VALEUR'] = pd.cut(
    df_filtered['VALEUR_CHEVAL'],
    bins=[0, 18, 24, 30, 34, float('inf')],
    labels=['[0,18]', ']18,24]', ']24,30]', ']30,34]', '34+'],
    include_lowest=True
)

# Créer un tableau groupé
table_valeur = df_filtered.groupby(
    ['CODE_RACE_CHEVAL', 'CODE_AGE_CHEVAL', 'CODE_ORIGINE_CHEVAL', 'PLAGE_VALEUR'],
    
    dropna=False
).agg({
    'ID_CHEVAL': 'count',
    'VALEUR_CHEVAL': ['mean', 'min', 'max']
}).reset_index()

table_valeur.columns = ['Race', 'Âge', 'Origine', 'Plage Valeur', 'Nombre Chevaux', 'Valeur Moyenne', 'Valeur Min', 'Valeur Max']

# Formater les valeurs
table_valeur['Valeur Moyenne'] = table_valeur['Valeur Moyenne'].apply(lambda x: f"{x:,.0f}")
table_valeur['Valeur Min'] = table_valeur['Valeur Min'].apply(lambda x: f"{x:,.0f}")
table_valeur['Valeur Max'] = table_valeur['Valeur Max'].apply(lambda x: f"{x:,.0f}")

# Réorganiser les colonnes
table_valeur = table_valeur[['Plage Valeur', 'Race', 'Âge', 'Origine', 'Nombre Chevaux']]

# Déboguer: vérifier si des données existent
if len(table_valeur) == 0:
    st.warning("⚠️ Le tableau est vide. Vérifiez les filtres appliqués.")
else:
    # Afficher le tableau
    st.dataframe(
        table_valeur,
        use_container_width=True,
        hide_index=True
    )

st.markdown("---")

# Footer
st.markdown("""
    <div style="text-align: center; color: gray; margin-top: 50px;">
    <p>📊 Outil d'analyse Performance Chevaux 2025 | Données: {0} chevaux</p>
    </div>
""".format(len(df_filtered)), unsafe_allow_html=True)
