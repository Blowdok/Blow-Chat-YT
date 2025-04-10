import configparser
import os
import pickle
import queue
import re
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import parse_qs, urlparse

import customtkinter as ctk
import faiss
import numpy as np
import PyPDF2
import requests
from colorama import Fore, Style
from googleapiclient.discovery import build
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
from youtube_transcript_api import YouTubeTranscriptApi

# Dictionnaire des couleurs disponibles
colors = {
    'Noir': '#000000',
    'Blanc': '#FFFFFF',
    'Rouge': '#FF0000',
    'Vert': '#008000',
    'Bleu': '#0000FF',
    'Jaune': '#FFFF00',
    'Orange': '#FFA500',
    'Violet': '#800080',
    'Gris': '#808080',
    'Rose': '#FFC0CB',
    'Marron': '#A52A2A',
    'Cyan': '#00FFFF',
    'Magenta': '#FF00FF',
}

# Initialiser CustomTkinter
ctk.set_appearance_mode("system")  # system, light, dark
ctk.set_default_color_theme("blue")  # blue, green, dark-blue

# Créer la fenêtre principale
app = ctk.CTk()
app.title("Blow Chat YT - V 1.1 - By BlowCoder - 2025")
app.geometry("1220x800")
app.minsize(1220, 800)

# Stocker l'historique des messages pour la mémoire du modèle
conversation_history = []

# Fonction pour créer les répertoires si besoin
def create_directories():
    if not os.path.exists("1_history_pkl"):
        os.makedirs("1_history_pkl")
    if not os.path.exists("2_conversation_txt"):
        os.makedirs("2_conversation_txt")
    if not os.path.exists("3_transcriptions"):
        os.makedirs("3_transcriptions")
    if not os.path.exists("4_markdown_reports"):
        os.makedirs("4_markdown_reports")
    if not os.path.exists("5_database"):
        os.makedirs("5_database")

# Créer les répertoires nécessaires
create_directories()

# Chemin du dossier history_pkl
history_folder = "1_history_pkl"
history_files = os.path.join(history_folder, "memo.pkl")

# Configurer le fichier de configuration
config = configparser.ConfigParser()
config_file = "config.ini"

# Variables thèmes
theme_var = ctk.StringVar(value="blue")

# Variables taille de la police
size_var = ctk.StringVar(value="19")

# Variables pour les couleurs des messages (initialisées avec les noms de couleurs)
color_system_var = ctk.StringVar(value='Bleu')        # Bleu par défaut
color_user_var = ctk.StringVar(value='Vert')          # Vert par défaut
color_model_var = ctk.StringVar(value='Rouge')        # Rouge par défaut
color_model_name_var = ctk.StringVar(value='Violet')  # Violet par défaut
color_user_name_var = ctk.StringVar(value='Orange')   # Orange par défaut

# Dictionnaire pour stocker les variables de couleur
color_vars = {
    'system': color_system_var,
    'user': color_user_var,
    'model': color_model_var,
    'model_name': color_model_name_var,
    'user_name': color_user_name_var,
}

# Variables pour le nom, le rôle et l'objectif du modèle
model_name_var = ctk.StringVar(value="LIHA")
model_role_var = ctk.StringVar(value="Assistant")
model_objective_var = ctk.StringVar(value="Aider les utilisateurs")

# Variables pour les clés API
youtube_api_key = ctk.StringVar()
groq_api_key = ctk.StringVar()

# Charger la configuration du fichier config.ini
def load_config():
    if os.path.exists(config_file):
        config.read(config_file)
    else:
        # créer une configuration par défaut
        config['API_KEYS'] = {}
        config['Appearance'] = {}
        config['Assistant'] = {}
        save_config()

    # Vérifier si les sections sont présentes, sinon les créer
    if 'Appearance' not in config:
        config['Appearance'] = {}
    if 'Assistant' not in config:
        config['Assistant'] = {}
    if 'API_KEYS' not in config:
        config['API_KEYS'] = {}

    # Charger les paramètres d'apparence
    theme = config.get('Appearance', 'theme', fallback='blue')
    font_size = config.get('Appearance', 'font_size', fallback='12')
    theme_var.set(theme)
    size_var.set(font_size)

    # Charger les couleurs des messages
    color_system = config.get('Appearance', 'color_system', fallback=colors['Bleu'])
    color_user = config.get('Appearance', 'color_user', fallback=colors['Vert'])
    color_model = config.get('Appearance', 'color_model', fallback=colors['Rouge'])
    color_model_name = config.get('Appearance', 'color_model_name', fallback=colors['Violet'])
    color_user_name = config.get('Appearance', 'color_user_name', fallback=colors['Orange'])

    # Mettre à jour les variables tkinter avec les noms de couleurs
    for color_var, color_value in zip(
        [color_system_var, color_user_var, color_model_var, color_model_name_var, color_user_name_var],
        [color_system, color_user, color_model, color_model_name, color_user_name]
    ):
        # Trouver le nom de la couleur correspondant au code hexadécimal
        for name, hex_value in colors.items():
            if hex_value == color_value:
                color_var.set(name)
                break
        else:
            # Si la couleur n'est pas trouvée, utiliser le code hexadécimal directement
            color_var.set(color_value)

    # Charger les clés API
    youtube_api_key.set(config.get('API_KEYS', 'youtube_api_key', fallback=''))
    groq_api_key.set(config.get('API_KEYS', 'groq_api_key', fallback=''))

    # Charger les paramètres de l'assistant
    model_name_var.set(config.get('Assistant', 'name', fallback='LIHA'))
    model_role_var.set(config.get('Assistant', 'role', fallback='Assistant'))
    model_objective_var.set(config.get('Assistant', 'objective', fallback='Aider l\'utilisateur'))

# Sauvegarder la configuration dans le fichier config.ini
def save_config():
    with open(config_file, 'w') as f:
        config.write(f)

# Fonction pour appliquer les paramètres chargés à l'interface
def apply_loaded_config():
    # Appliquer le thème
    theme = theme_var.get()
    ctk.set_default_color_theme(theme)

    # Appliquer la taille de la police
    font_size = int(size_var.get())
    new_font = ("Arial", font_size)

    # Appliquer la nouvelle police aux widgets concernés
    text_output.configure(font=new_font)
    entry.configure(font=new_font)
    # Vous pouvez ajouter d'autres widgets si nécessaire, par exemple les boutons, etc.

    # Appliquer les couleurs aux tags
    # Mettre à jour les tags avec les couleurs chargées
    text_output._textbox.tag_config('system', foreground=colors.get(color_system_var.get(), color_system_var.get()))
    text_output._textbox.tag_config('user', foreground=colors.get(color_user_var.get(), color_user_var.get()))
    text_output._textbox.tag_config('model', foreground=colors.get(color_model_var.get(), color_model_var.get()))
    text_output._textbox.tag_config('model_name', foreground=colors.get(color_model_name_var.get(), color_model_name_var.get()))
    text_output._textbox.tag_config('user_name', foreground=colors.get(color_user_name_var.get(), color_user_name_var.get()))

# Fonction pour sauvegarder l'historique de conversation
def save_history():
    try:
        with open(history_files, 'wb') as f:
            pickle.dump(conversation_history, f)
        print("Historique de conversation sauvegardé automatiquement.")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de l'historique : {e}")

# Fonction pour charger l'historique de conversation
def load_history():
    global conversation_history
    if os.path.exists(history_files):
        try:
            with open(history_files, 'rb') as f:
                conversation_history = pickle.load(f)
            print("Historique de conversation chargé automatiquement.")
            # Mettre à jour l'interface utilisateur
            update_conversation_display()
        except Exception as e:
            print(f"Erreur lors du chargement de l'historique : {e}")
    else:
        conversation_history = []

# Fonction pour mettre à jour l'affichage de la conversation
def update_conversation_display():
    assistant_name = model_name_var.get()
    text_output._textbox.delete("1.0", ctk.END)
    for message in conversation_history:
        if isinstance(message, HumanMessage):
            # Afficher le message de l'utilisateur
            text_output._textbox.insert(ctk.END, "Boss: ", 'user_name')
            text_output._textbox.insert(ctk.END, f"{message.content}\n\n", 'user')
        elif isinstance(message, AIMessage):
            # Afficher la réponse de l'assistant
            text_output._textbox.insert(ctk.END, f"{assistant_name}: ", 'model_name')
            text_output._textbox.insert(ctk.END, f"{message.content}\n\n", 'model')
    text_output._textbox.see(ctk.END)

def reset_history():
    global conversation_history
    conversation_history = []
    # Supprimer le fichier d'historique
    if os.path.exists(history_files):
        os.remove(history_files)
    messagebox.showinfo("Information", "L'historique de conversation a été réinitialisé.")

# Fonction pour charger la clé API Groq depuis la variable de configuration
def get_groq_api_key():
    return groq_api_key.get()

# Fonction pour charger la clé API YouTube depuis la variable de configuration
def get_youtube_api_key():
    return youtube_api_key.get()

def load_vector_database(db_filename='transcript_vectors.pkl'):
    """
    Charge la base de données vectorielle et l'index FAISS.
    """
    # Chemins des fichiers
    index_path = os.path.join('5_database', 'faiss_index.bin')
    db_path = os.path.join('5_database', db_filename)

    # Charger l'index FAISS
    index = faiss.read_index(index_path)
    # Charger les métadonnées
    with open(db_path, 'rb') as f:
        data = pickle.load(f)
    return index, data


# Fonction pour rechercher les documents pertinents
def search_documents(query, index, data, top_k=10, max_context_length=3500):
    """
    Recherche les documents les plus pertinents pour une requête donnée.
    Limite la longueur totale du contexte.
    """
    # Encoder la requête
    model = SentenceTransformer('all-MiniLM-L6-v2')
    query_vector = model.encode([query])

    # Recherche dans l'index
    distances, indices = index.search(query_vector, top_k * 100)  # Obtenir plus de résultats pour filtrer ensuite
    results = []
    total_length = 0
    for idx in indices[0]:
        document = data['documents'][idx]
        doc_length = len(document)
        if total_length + doc_length > max_context_length:
            break
        results.append(document)
        total_length += doc_length
    return results

def count_tokens(text):
    # Cette fonction compte approximativement le nombre de tokens dans le texte
    # En supposant qu'un token correspond à environ 4 caractères en moyenne
    return len(text) // 4


# Fonction pour générer la réponse du modèle
def generate_answer(query, context, text_widget, model_name='meta-llama/llama-4-scout-17b-16e-instruct', groq_api_key=None):
    """Génère une réponse en utilisant le modèle Groq via langchain-groq avec le streaming."""
    q = queue.Queue()
    

    def insert_text():
        try:
            while True:
                text, tag = q.get_nowait()
                if text:
                    text_widget._textbox.insert(ctk.END, text, tag)
                    text_widget._textbox.see(ctk.END)
                    text_widget._textbox.update_idletasks()
        except queue.Empty:
            pass
        finally:
            if thread.is_alive():
                speed = speed_var.get()
                if speed == "Lent":
                    interval = 1000  # 1 seconde
                elif speed == "Normal":
                    interval = 500   # 0,5 seconde
                elif speed == "Rapide":
                    interval = 100   # 0,1 seconde
                elif speed == "Très Rapide":
                    interval = 50    # 0,05 seconde
                elif speed == "Turbo":
                    interval = 10     # 0,01 seconde
                else:
                    interval = 500  # Valeur par défaut (0,5 seconde)
                text_widget.after(interval, insert_text)

    def run_model():
        if not groq_api_key:
            q.put(("La clé API Groq n'a pas été fournie.\n\n", 'system'))
            return

        os.environ['GROQ_API_KEY'] = groq_api_key

        # Construire les messages en incluant l'historique
        messages = []

        # Ajouter le message système initial avec le rôle et l'objectif
        assistant_name = model_name_var.get()
        assistant_role = model_role_var.get()
        assistant_objective = model_objective_var.get()
        system_prompt = f"{assistant_name}. Tu es {assistant_role}. Ton objectif est : {assistant_objective}."
        if context:
            system_prompt += f"\n\nContexte :\n{context}"
        messages.append(SystemMessage(content=system_prompt))
        
        # Vérifier la taille du system_prompt
        token_count = count_tokens(system_prompt)
        if token_count > 18000:
            q.put(("\nLe contexte est trop volumineux pour le modèle. Veuillez réduire la taille du contexte.\n", 'system'))
            return

        # Ajouter l'historique de la conversation
        messages.extend(conversation_history)

        try:
            llm = ChatGroq(
                model=model_name,
                temperature=0.5,
                max_tokens=6000,
                timeout=None,
                max_retries=2,
                streaming=True,  # Activer le streaming
            )

            # Insérer le nom du modèle avec le tag 'model_name'
            assistant_name = model_name_var.get()
            q.put((f"{assistant_name}: ", 'model_name'))

            # Utiliser le streaming pour recevoir les tokens au fur et à mesure
            response_stream = llm.stream(messages)

            response_content = ''
            for chunk in response_stream:
                token = chunk.content  # Récupérer le token généré
                response_content += token
                q.put((token, 'model'))

            q.put(("\n\n", 'model'))

            # Ajouter la réponse du modèle à l'historique
            conversation_history.append(AIMessage(content=response_content))

            # Limiter la taille de l'historique si nécessaire
            max_history_length = 5  # Vous pouvez ajuster ce nombre
            if len(conversation_history) > max_history_length * 2:
                # Supprimer les messages les plus anciens
                conversation_history[:] = conversation_history[-max_history_length*2:]

        except Exception as e:
            q.put((f"\nErreur lors de l'appel à Groq : {e}\n\n", 'system'))

    thread = threading.Thread(target=run_model)
    thread.start()

    text_widget.after(100, insert_text)

# Fonction pour gérer l'envoi du message
def on_submit(event=None):
    query = entry.get()
    if query.lower() == 'exit':
        app.destroy()
        return

    # Effacer le champ de saisie
    entry.delete(0, ctk.END)

    # Insérer le nom de l'utilisateur avec le tag 'user_name'
    text_output._textbox.insert(ctk.END, "Boss: ", 'user_name')
    # Insérer la question de l'utilisateur avec le tag 'user'
    text_output._textbox.insert(ctk.END, f"{query}\n\n", 'user')
    text_output._textbox.see(ctk.END)

    # Ajouter le message de l'utilisateur à l'historique
    conversation_history.append(HumanMessage(content=query))

    # Obtenir le contexte si la base de données est utilisée
    context = ''
    if use_database.get():
        if index is None or data is None:
            text_output._textbox.insert(ctk.END, "La base de données n'est pas chargée. Veuillez la charger d'abord.\n", 'system')
            context = ''
        else:
            try:
                # Vous pouvez ajuster top_k et max_context_length selon vos besoins
                documents = search_documents(query, index, data, top_k=5, max_context_length=3000)
                context = "\n".join(documents)
            except Exception as e:
                text_output._textbox.insert(ctk.END, f"Erreur lors de la recherche dans la base de données : {e}\n", 'system')

    # Appeler generate_answer (il gère le threading en interne)
    generate_answer(query, context, text_output, model_name.get(), groq_api_key.get())

# Fonction pour charger la base de données
def load_database():
    global index, data
    try:
        index, data = load_vector_database()
        use_database.set(True)
        messagebox.showinfo("Succès", "Base de données chargée avec succès.")
    except Exception as e:
        messagebox.showerror("Erreur", f"Erreur lors du chargement de la base de données : {e}")
        use_database.set(False)

# Fonction pour sauvegarder la conversation manuellement
def save_conversation():
    file_path = filedialog.asksaveasfilename(defaultextension=".pkl", filetypes=[("Pickle Files", "*.pkl")])
    if file_path:
        try:
            with open(file_path, 'wb') as f:
                pickle.dump({
                    'text': text_output._textbox.get("1.0", ctk.END),
                    'history': conversation_history
                }, f)
            messagebox.showinfo("Succès", "Conversation sauvegardée avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde de la conversation : {e}")

# Fonction pour charger une conversation manuellement
def load_conversation():
    file_path = filedialog.askopenfilename(filetypes=[("Pickle Files", "*.pkl")])
    if file_path:
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            text_output._textbox.delete("1.0", ctk.END)
            text_output._textbox.insert(ctk.END, data['text'])
            global conversation_history
            conversation_history = data.get('history', [])
            messagebox.showinfo("Succès", "Conversation chargée avec succès.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement de la conversation : {e}")

# Fonction pour effacer la conversation
def clear_conversation():
    text_output._textbox.delete("1.0", ctk.END)
    # Ne pas effacer conversation_history pour conserver l'historique

# Fonction pour ouvrir la fenêtre des paramètres
def open_settings():
    settings_window = ctk.CTkToplevel(app)
    settings_window.title("Paramètres")
    settings_window.geometry("400x300")

    # Label et Entry pour les clés API
    youtube_api_label = ctk.CTkLabel(settings_window, text="YouTube API Key:")
    youtube_api_label.pack(pady=5)
    youtube_api_entry = ctk.CTkEntry(settings_window, width=300, textvariable=youtube_api_key)
    youtube_api_entry.pack(pady=5)

    groq_api_label = ctk.CTkLabel(settings_window, text="Groq API Key:")
    groq_api_label.pack(pady=5)
    groq_api_entry = ctk.CTkEntry(settings_window, width=300, textvariable=groq_api_key)
    groq_api_entry.pack(pady=5)

    def save_api_keys():
        config['API_KEYS']['youtube_api_key'] = youtube_api_key.get()
        config['API_KEYS']['groq_api_key'] = groq_api_key.get()
        save_config()
        messagebox.showinfo("Succès", "Clés API sauvegardées avec succès.")

    def reset_api_keys():
        youtube_api_key.set('')
        groq_api_key.set('')

    save_button = ctk.CTkButton(settings_window, text="Sauvegarder", command=save_api_keys)
    save_button.pack(pady=5)

    reset_button = ctk.CTkButton(settings_window, text="Réinitialiser", command=reset_api_keys)
    reset_button.pack(pady=5)

# Fonction pour ouvrir les paramètres de l'assistant
def open_assistant_settings():
    assistant_window = ctk.CTkToplevel(app)
    assistant_window.title("Paramètres de l'assistant")
    assistant_window.geometry("400x300")

    name_label = ctk.CTkLabel(assistant_window, text="Nom de l'assistant :")
    name_label.pack(pady=5)
    name_entry = ctk.CTkEntry(assistant_window, width=300, textvariable=model_name_var)
    name_entry.pack(pady=5)

    role_label = ctk.CTkLabel(assistant_window, text="Rôle de l'assistant :")
    role_label.pack(pady=5)
    role_entry = ctk.CTkEntry(assistant_window, width=300, textvariable=model_role_var)
    role_entry.pack(pady=5)

    objective_label = ctk.CTkLabel(assistant_window, text="Objectif de l'assistant :")
    objective_label.pack(pady=5)
    objective_entry = ctk.CTkEntry(assistant_window, width=300, textvariable=model_objective_var)
    objective_entry.pack(pady=5)

    def save_assistant_settings():
        config['Assistant']['name'] = model_name_var.get()
        config['Assistant']['role'] = model_role_var.get()
        config['Assistant']['objective'] = model_objective_var.get()
        save_config()
        messagebox.showinfo("Succès", "Paramètres de l'assistant sauvegardés avec succès.")
        assistant_window.destroy()

    save_button = ctk.CTkButton(assistant_window, text="Sauvegarder", command=save_assistant_settings)
    save_button.pack(pady=10)

# Fonction pour changer les couleurs du thème
def change_colors():
    colors_window = ctk.CTkToplevel(app)
    colors_window.title("Changer les couleurs")
    colors_window.geometry("300x300")

    theme_label = ctk.CTkLabel(colors_window, text="Sélectionner le thème:")
    theme_label.pack(pady=5)

    themes = ["blue", "green", "dark-blue"]

    def apply_theme():
        theme = theme_var.get()
        ctk.set_default_color_theme(theme)
        # Sauvegarder le thème dans la configuration
        config['Appearance']['theme'] = theme
        save_config()
        messagebox.showinfo("Succès", f"Thème '{theme}' appliqué.")
        colors_window.destroy()

    theme_dropdown = ctk.CTkOptionMenu(colors_window, values=themes, variable=theme_var)
    theme_dropdown.pack(pady=5)

    apply_button = ctk.CTkButton(colors_window, text="Appliquer", command=apply_theme)
    apply_button.pack(pady=5)

# Fonction pour changer la police et la taille
def change_font():
    font_window = ctk.CTkToplevel(app)
    font_window.title("Changer la police et la taille")
    font_window.geometry("300x300")

    size_label = ctk.CTkLabel(font_window, text="Sélectionner la taille de la police:")
    size_label.pack(pady=5)

    sizes = [str(s) for s in range(8, 25)]

    def apply_font():
        size = int(size_var.get())
        # Appliquer la taille de la police aux widgets
        new_font = ("Arial", size)
        text_output.configure(font=new_font)
        entry.configure(font=new_font)
        # Sauvegarder la taille de la police dans la configuration
        config['Appearance']['font_size'] = str(size)
        save_config()
        messagebox.showinfo("Succès", f"Police de taille {size} appliquée.")
        font_window.destroy()

    size_dropdown = ctk.CTkOptionMenu(font_window, values=sizes, variable=size_var)
    size_dropdown.pack(pady=5)

    apply_button = ctk.CTkButton(font_window, text="Appliquer", command=apply_font)
    apply_button.pack(pady=5)

# Fonction pour personnaliser les couleurs des messages
def open_color_customization():
    color_window = ctk.CTkToplevel(app)
    color_window.title("Personnaliser les couleurs")
    color_window.geometry("400x400")

    # Listes des noms de couleurs pour les menus déroulants
    color_names = list(colors.keys())

    # Widgets pour chaque type de message
    def create_color_option(label_text, color_var):
        frame = ctk.CTkFrame(color_window)
        frame.pack(pady=5, padx=5, fill='x')
        label = ctk.CTkLabel(frame, text=label_text)
        label.pack(side='left', padx=5)
        option_menu = ctk.CTkOptionMenu(
            frame,
            values=color_names,
            variable=color_var,
            command=lambda _: update_color_preview(color_var, preview_label)
        )
        option_menu.pack(side='left', padx=5)
        preview_label = ctk.CTkLabel(frame, text="    ", width=10)
        preview_label.pack(side='left', padx=5)
        update_color_preview(color_var, preview_label)

    def update_color_preview(color_var, label):
        color_hex = colors.get(color_var.get(), color_var.get())
        label.configure(bg_color=color_hex)

    # Créer les options pour chaque type de message
    create_color_option("Couleur des messages système :", color_system_var)
    create_color_option("Couleur des entrées utilisateur :", color_user_var)
    create_color_option("Couleur des réponses du modèle :", color_model_var)
    create_color_option("Couleur du nom du modèle :", color_model_name_var)
    create_color_option("Couleur du nom de l'utilisateur :", color_user_name_var)

    def apply_colors():
        # Fonction pour obtenir la valeur de couleur (code hexadécimal)
        def get_color_value(color_var):
            color_value = color_var.get()
            # Si le nom de couleur est dans le dictionnaire, obtenir le code hexadécimal
            if color_value in colors:
                return colors[color_value]
            else:
                # Sinon, on suppose que c'est un code hexadécimal
                return color_value

        # Obtenir les valeurs de couleur
        color_system = get_color_value(color_system_var)
        color_user = get_color_value(color_user_var)
        color_model = get_color_value(color_model_var)
        color_model_name = get_color_value(color_model_name_var)
        color_user_name = get_color_value(color_user_name_var)

        # Mettre à jour les tags avec les nouvelles couleurs
        text_output._textbox.tag_config('system', foreground=color_system)
        text_output._textbox.tag_config('user', foreground=color_user)
        text_output._textbox.tag_config('model', foreground=color_model)
        text_output._textbox.tag_config('model_name', foreground=color_model_name)
        text_output._textbox.tag_config('user_name', foreground=color_user_name)

        # Sauvegarder les couleurs dans la configuration
        config['Appearance']['color_system'] = color_system
        config['Appearance']['color_user'] = color_user
        config['Appearance']['color_model'] = color_model
        config['Appearance']['color_model_name'] = color_model_name
        config['Appearance']['color_user_name'] = color_user_name
        save_config()
        messagebox.showinfo("Succès", "Couleurs appliquées et sauvegardées.")
        color_window.destroy()

    apply_button = ctk.CTkButton(color_window, text="Appliquer", command=apply_colors)
    apply_button.pack(pady=10)

# Fonction pour afficher les messages d'information dans la zone de texte ou dans la console
def log_info(message, text_widget=None):
    if text_widget:
        text_widget.insert(ctk.END, f"[INFO] {message}\n")
        text_widget.see(ctk.END)
    else:
        print(f"[INFO] {message}")

# Fonction pour afficher les messages d'erreur dans la zone de texte ou dans la console
def log_error(message, text_widget=None):
    if text_widget:
        text_widget.insert(ctk.END, f"[ERROR] {message}\n")
        text_widget.see(ctk.END)
    else:
        print(f"[ERROR] {message}")

# Fonction pour nettoyer le nom de fichier en supprimant les caractères non valides et en remplaçant les espaces
def clean_filename(filename):
    filename = filename.strip()
    return re.sub(r'[<>:"/\\|?*@]', '', filename).replace(' ', '_')


# Fonction pour récupérer les vidéos à partir de la playlist
def get_videos_from_playlist(playlist_id, api_key, max_videos=None):
    youtube = build('youtube', 'v3', developerKey=api_key)
    videos = []
    nextPageToken = None

    while True:
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=playlist_id,
            maxResults=50,
            pageToken=nextPageToken
        )
        response = request.execute()

        videos.extend(response['items'])

        nextPageToken = response.get('nextPageToken')
        if not nextPageToken or (max_videos and len(videos) >= max_videos):
            break

    return videos[:max_videos] if max_videos else videos


def get_videos_youtube(channel_name, api_key, num_videos):
    youtube = build('youtube', 'v3', developerKey=api_key)

    # Obtenir l'ID du channel à partir du nom
    request = youtube.search().list(
        part="snippet",
        q=channel_name,
        type="channel",
        maxResults=1
    )
    response = request.execute()

    if not response['items']:
        raise Exception(f"Channel non trouvé pour le nom {channel_name}")

    channel_id = response['items'][0]['id']['channelId']

    # Obtenir l'ID de la playlist des uploads
    uploads_playlist_id = get_channel_uploads_playlist_id(channel_id, api_key)

    # Obtenir les vidéos de la playlist des uploads
    playlist_videos = get_videos_from_playlist(uploads_playlist_id, api_key, max_videos=num_videos)

    video_ids = [item['contentDetails']['videoId'] for item in playlist_videos]

    # Obtenir les détails et statistiques des vidéos
    videos = []
    for i in range(0, len(video_ids), 50):
        batch_ids = video_ids[i:i+50]
        stats_request = youtube.videos().list(
            part="snippet,statistics",
            id=','.join(batch_ids)
        )
        stats_response = stats_request.execute()
        videos.extend(stats_response['items'])

    return videos


# Fonction pour récupérer les transcriptions des vidéos via les sous-titres
def get_transcription(video_id, languages=['en', 'fr'], text_widget=None):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages)
        transcript = " ".join([item['text'] for item in transcript_list])
        return transcript
    except Exception as e:
        log_error(f"Impossible de récupérer la transcription pour la vidéo {video_id}: {e}", text_widget)
        return None

# Fonction pour sauvegarder la transcription dans un fichier texte en UTF-8
def save_transcription(video_id, transcription, text_widget):
    transcription_file = f"3_transcriptions/{video_id}.txt"
    with open(transcription_file, "w", encoding='utf-8') as f:
        f.write(transcription)
    log_info(f"Transcription sauvegardée dans {transcription_file}", text_widget)

# Mise à jour de la fonction generate_markdown_report
def generate_markdown_report(video, transcription, stats, text_widget):
    video_id = video['id']
    report_content = f"# Rapport de la vidéo : {video['snippet']['title']}\n\n"
    report_content += f"- **Date de publication** : {video['snippet']['publishedAt']}\n"
    report_content += f"- **Description** : {video['snippet']['description']}\n"
    report_content += f"- **Lien** : [https://www.youtube.com/watch?v={video_id}](https://www.youtube.com/watch?v={video_id})\n"
    report_content += f"- **Vues** : {stats['viewCount']}\n"
    #report_content += f"- **Likes** : {stats['likeCount']}\n"
    #report_content += f"- **Partages** : {stats.get('shareCount', 'Non disponible')}\n"
    report_content += f"- **Abonnés** : {stats.get('subscriberCount', 'Non disponible')}\n"
    report_content += f"- **Transcription (extrait)** :\n```\n{transcription[:500]}...\n```\n"

    report_file = f"4_markdown_reports/{video_id}_report.md"
    with open(report_file, "w", encoding='utf-8') as f:
        f.write(report_content)

    log_info(f"Rapport markdown généré : {report_file}", text_widget)

# Fonction pour transformer les transcriptions en embeddings et les stocker dans FAISS


def create_vector_database(transcripts_folder='3_transcriptions', db_filename='transcript_vectors.pkl', chunk_size=500):
    """
    Crée une base de données vectorielle à partir des transcriptions et des PDF.
    Les documents sont divisés en chunks de taille spécifiée.
    """
    # Charger le modèle de transformation
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Lire toutes les transcriptions et les PDF
    documents = []
    filenames = []
    metadata = []
    for filename in os.listdir(transcripts_folder):
        filepath = os.path.join(transcripts_folder, filename)
        if filename.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        elif filename.endswith('.pdf'):
            with open(filepath, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ''
                for page in reader.pages:
                    text += page.extract_text()
        else:
            continue  # Ignorer les autres types de fichiers

        # Diviser le texte en chunks
        text_chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        documents.extend(text_chunks)
        filenames.extend([filename] * len(text_chunks))
        metadata.extend([{'filename': filename, 'chunk_index': idx} for idx in range(len(text_chunks))])

    # Encoder les documents en vecteurs
    vectors = model.encode(documents)

    # Créer le dossier database s'il n'existe pas
    if not os.path.exists('5_database'):
        os.makedirs('5_database')

    # Chemins des fichiers
    index_path = os.path.join('5_database', 'faiss_index.bin')
    db_path = os.path.join('5_database', db_filename)

    # Créer l'index FAISS
    dimension = vectors.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(vectors)

    # Sauvegarder l'index et les métadonnées
    faiss.write_index(index, index_path)
    with open(db_path, 'wb') as f:
        pickle.dump({'filenames': filenames, 'documents': documents, 'metadata': metadata}, f)




# Fonction pour démarrer l'outil de création de base de données
def start_database_tool():
    try:
        create_vector_database()
        database_output._textbox.insert(ctk.END, "Base de données vectorielle créée avec succès.\n")
    except Exception as e:
        database_output._textbox.insert(ctk.END, f"Erreur lors de la création de la base de données : {e}\n")


# Fonction pour obtenir l'ID de la playlist
def get_channel_uploads_playlist_id(channel_id, api_key):
    youtube = build('youtube', 'v3', developerKey=api_key)
    request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    response = request.execute()
    uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    return uploads_playlist_id



# Fonction pour démarrer l'outil YouTube
def start_youtube_tool():
    channel_name = channel_id_entry.get()
    api_key = youtube_api_key.get()
    num_videos = int(num_videos_entry.get())
    video_ids_input = video_ids_entry.get()
    if not api_key:
        messagebox.showerror("Erreur", "La clé API YouTube n'est pas définie.")
        return
    if video_ids_input.strip():
        # L'utilisateur a spécifié des vidéos
        video_ids = [vid.strip() for vid in video_ids_input.split(',')]
        videos = get_videos_by_ids(video_ids, api_key)
    else:
        # Utiliser le nom de la chaîne et le nombre de vidéos
        videos = get_videos_youtube(channel_name, api_key, num_videos)
    # Traitez les vidéos comme nécessaire
    for video in videos:
        video_id = video['id']
        transcription = get_transcription(video_id, ['en', 'fr'], youtube_output._textbox)
        if transcription:
            save_transcription(video_id, transcription, youtube_output._textbox)
            generate_markdown_report(video, transcription, video['statistics'], youtube_output._textbox)
    messagebox.showinfo("Succès", "Traitement des vidéos terminé.")


def extract_video_id(url):
    """
    Extrait l'ID de la vidéo à partir d'une URL YouTube ou retourne l'ID si déjà donné.
    """
    # Si c'est déjà un ID de 11 caractères, on le retourne
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url

    # Sinon, on essaie de le récupérer à partir de l'URL
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com', 'm.youtube.com']:
        if parsed_url.path == '/watch':
            query = parse_qs(parsed_url.query)
            if 'v' in query:
                return query['v'][0]
        elif parsed_url.path.startswith(('/embed/', '/v/')):
            return parsed_url.path.split('/')[2]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    else:
        return None


def get_videos_by_ids(video_ids, api_key):
    youtube = build('youtube', 'v3', developerKey=api_key)
    videos = []
    for video_id in video_ids:
        # Extraire l'ID de la vidéo
        extracted_id = extract_video_id(video_id)
        if not extracted_id:
            log_error(f"ID de vidéo invalide : {video_id}", youtube_output._textbox)
            continue
        request = youtube.videos().list(
            part="snippet,statistics",
            id=extracted_id
        )
        response = request.execute()
        if response['items']:
            video_data = response['items'][0]
            video_data['id'] = extracted_id  # Assurez-vous que l'ID est correct
            videos.append(video_data)
        else:
            log_error(f"Vidéo non trouvée pour l'ID {extracted_id}", youtube_output._textbox)
    return videos




def load_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
    if file_path:
        # Si votre modèle supporte le traitement d'images, vous pouvez le charger et l'envoyer au modèle
        with open(file_path, 'rb') as f:
            image_data = f.read()
        # Envoyer l'image au modèle
        # Vous devrez adapter cette partie en fonction des capacités de votre modèle
        messagebox.showinfo("Information", "Image chargée avec succès. Fonctionnalité à implémenter.")

# Initialiser les variables et composants

# Initialiser la variable use_database
use_database = ctk.BooleanVar(value=False)
index = None
data = None

model_options = [
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "qwen-2.5-coder-32b",
    "deepseek-r1-distill-qwen-32b",
    # ajouter d'autres modèles ici
]
model_name = ctk.StringVar(value=model_options[0])  # Modèle par défaut

# Barre de menus
menu_bar = tk.Menu(app)

# Apparence
appearance_menu = tk.Menu(menu_bar, tearoff=0)
appearance_menu.add_command(label="Changer le thème", command=change_colors)
appearance_menu.add_command(label="Changer la taille", command=change_font)
appearance_menu.add_command(label="Personnaliser les couleurs", command=open_color_customization)
menu_bar.add_cascade(label="Apparence", menu=appearance_menu)

# Paramètres
settings_menu = tk.Menu(menu_bar, tearoff=0)
settings_menu.add_command(label="Paramètres", command=open_settings)
settings_menu.add_command(label="Assistant", command=open_assistant_settings)
menu_bar.add_cascade(label="Paramètres", menu=settings_menu)

app.config(menu=menu_bar)

# Sidebar gauche
left_frame = ctk.CTkFrame(app, width=200)
left_frame.pack(side="left", fill="y")

# Sidebar droite
right_frame = ctk.CTkFrame(app, width=200)
right_frame.pack(side="right", fill="y")

# Zone de contenu principal
main_frame = ctk.CTkFrame(app)
main_frame.pack(side="left", fill="both", expand=True)

# Créer des onglets dans main_frame
notebook = ctk.CTkTabview(main_frame)
notebook.pack(fill="both", expand=True)

# Créer les onglets
assistant_tab = ctk.CTkFrame(notebook)
youtube_tab = ctk.CTkFrame(notebook)
database_tab = ctk.CTkFrame(notebook)

# Ajouter les onglets au notebook
assistant_tab = notebook.add("Assistant")
youtube_tab = notebook.add("Outil YouTube")
database_tab = notebook.add("Outil Base de Données")

# Widgets pour la sidebar gauche
db_label = ctk.CTkLabel(left_frame, text="Base de Données :")
db_label.pack(pady=5)
load_db_button = ctk.CTkButton(left_frame, text="Charger DB", command=load_database)
load_db_button.pack(pady=5, padx=5)

save_label = ctk.CTkLabel(left_frame, text="Sauvegarder :")
save_label.pack(pady=5)
save_conv_button = ctk.CTkButton(left_frame, text="Sauvegarder Chat", command=save_conversation)
save_conv_button.pack(pady=5, padx=5)

load_label = ctk.CTkLabel(left_frame, text="Charger :")
load_label.pack(pady=5)
load_conv_button = ctk.CTkButton(left_frame, text="Charger Chat", command=load_conversation)
load_conv_button.pack(pady=5, padx=5)

del_label = ctk.CTkLabel(left_frame, text="Effacer :")
del_label.pack(pady=5)
clear_conv_button = ctk.CTkButton(left_frame, text="Effacer Chat", command=clear_conversation)
clear_conv_button.pack(pady=5, padx=5)

reset_label = ctk.CTkLabel(left_frame, text="Réinitialiser :")
reset_label.pack(pady=5)
reset_history_button = ctk.CTkButton(left_frame, text="Réinitialiser Historique", command=reset_history)
reset_history_button.pack(pady=5, padx=5)

# Widgets pour la sidebar droite
param_label = ctk.CTkLabel(right_frame, text="Clés API :")
param_label.pack(pady=5)
settings_button = ctk.CTkButton(right_frame, text="Paramètres", command=open_settings)
settings_button.pack(pady=5, padx=5)

# Menu déroulant pour contrôler la vitesse du streaming
speed_label = ctk.CTkLabel(right_frame, text="Vitesse Stream :")
speed_label.pack(pady=5)

speed_options = ["Lent", "Normal", "Rapide", "Très Rapide", "Turbo"]

speed_var = ctk.StringVar(value="Normal")
speed_menu = ctk.CTkOptionMenu(right_frame, values=speed_options, variable=speed_var)
speed_menu.pack(pady=5)

model_label = ctk.CTkLabel(right_frame, text="Modèle:")
model_label.pack(pady=5)

model_dropdown = ctk.CTkOptionMenu(right_frame, values=model_options, variable=model_name)
model_dropdown.pack(pady=5)

# Widgets pour l'onglet Assistant
# Zone de texte pour afficher la conversation
text_output = ctk.CTkTextbox(assistant_tab, wrap=tk.WORD)
text_output.pack(fill='both', expand=True, pady=5)

# Définir les tags pour les styles en utilisant l'attribut _textbox
text_output._textbox.tag_config('system', foreground=colors.get(color_system_var.get(), color_system_var.get()))
text_output._textbox.tag_config('user', foreground=colors.get(color_user_var.get(), color_user_var.get()))
text_output._textbox.tag_config('model', foreground=colors.get(color_model_var.get(), color_model_var.get()))
text_output._textbox.tag_config('model_name', foreground=colors.get(color_model_name_var.get(), color_model_name_var.get()))
text_output._textbox.tag_config('user_name', foreground=colors.get(color_user_name_var.get(), color_user_name_var.get()))

# Zone d'entrée pour la question
input_frame = ctk.CTkFrame(assistant_tab)
input_frame.pack(fill="y", pady=5)

entry = ctk.CTkEntry(input_frame, width=700)
entry.pack(side="left", fill="y", expand=True, padx=5)

send_button = ctk.CTkButton(input_frame, text="Envoyer", command=on_submit)
send_button.pack(side="left", expand=True, padx=5)

# Lier la touche Entrée au bouton Envoyer
entry.bind("<Return>", on_submit)

# Case à cocher pour utiliser la base de données
use_db_checkbox = ctk.CTkCheckBox(assistant_tab, text="Utiliser la base de données pour améliorer les réponses", variable=use_database)
use_db_checkbox.pack(pady=5)

# Widgets pour l'onglet Outil YouTube
youtube_label = ctk.CTkLabel(youtube_tab, text="Outil de récupération d'informations et transcription YouTube")
youtube_label.pack(pady=5)

channel_id_label = ctk.CTkLabel(youtube_tab, text="Nom ou ID de la chaîne YouTube:")
channel_id_label.pack(pady=5)
channel_id_entry = ctk.CTkEntry(youtube_tab, width=300)
channel_id_entry.pack(pady=5)

video_ids_label = ctk.CTkLabel(youtube_tab, text="IDs ou URLs des vidéos (séparés par des virgules) :")
video_ids_label.pack(pady=5)
video_ids_entry = ctk.CTkEntry(youtube_tab, width=300)
video_ids_entry.pack(pady=5)


num_videos_label = ctk.CTkLabel(youtube_tab, text="Nombre de vidéos à récupérer:")
num_videos_label.pack(pady=5)
num_videos_entry = ctk.CTkEntry(youtube_tab, width=100)
num_videos_entry.pack(pady=5)
num_videos_entry.insert(0, "5")

start_button = ctk.CTkButton(youtube_tab, text="Démarrer", command=start_youtube_tool)
start_button.pack(pady=5)

youtube_output = ctk.CTkTextbox(youtube_tab)
youtube_output.pack(fill='both', expand=True, pady=5)

# Widgets pour l'onglet Outil Base de Données
database_label = ctk.CTkLabel(database_tab, text="Outil pour transformer les textes en base de données pour le modèle")
database_label.pack(pady=5)

start_db_button = ctk.CTkButton(database_tab, text="Créer la base de données", command=start_database_tool)
start_db_button.pack(pady=5)

database_output = ctk.CTkTextbox(database_tab)
database_output.pack(fill='both', expand=True, pady=5)

# Charger la configuration avant la création des widgets
load_config()

# Appliquer la taille de la police initiale
new_font = ("Arial", int(size_var.get()))

# Appliquer les paramètres chargés après la création des widgets
apply_loaded_config()

# Charger l'historique de conversation
load_history()

# Nettoyer la zone de texte pour commencer une nouvelle conversation
text_output._textbox.delete("1.0", ctk.END)

# Gérer la fermeture de l'application
def on_closing():
    save_history()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)

# Lancer la boucle d'événements GUI
app.mainloop()
