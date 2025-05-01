"""
Module interface.py - Définition de l'interface graphique pour l'application Blow Chat YT
Contient la classe principale pour l'interface utilisateur et tous les widgets nécessaires.
"""

import os
import re
import sys
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import filedialog, messagebox

import customtkinter as ctk


class BlowChatInterface:
    """Classe principale pour l'interface graphique de Blow Chat YT"""
    
    def __init__(self, 
                 on_submit_callback, 
                 on_load_database_callback, 
                 on_save_conversation_callback,
                 on_load_conversation_callback, 
                 on_clear_conversation_callback,
                 on_reset_history_callback, 
                 on_start_youtube_tool_callback,
                 on_start_database_tool_callback,
                 on_closing_callback,
                 on_enrich_database_callback,
                 on_get_available_databases_callback,
                 on_get_available_sources_callback):
        """
        Initialisation de l'interface graphique
        
        Args:
            on_submit_callback: Fonction à appeler lors de l'envoi d'un message
            on_load_database_callback: Fonction à appeler pour charger la base de données
            on_save_conversation_callback: Fonction à appeler pour sauvegarder la conversation
            on_load_conversation_callback: Fonction à appeler pour charger une conversation
            on_clear_conversation_callback: Fonction à appeler pour effacer la conversation
            on_reset_history_callback: Fonction à appeler pour réinitialiser l'historique
            on_start_youtube_tool_callback: Fonction à appeler pour démarrer l'outil YouTube
            on_start_database_tool_callback: Fonction à appeler pour créer la base de données
            on_closing_callback: Fonction à appeler lors de la fermeture de l'application
            on_enrich_database_callback: Fonction à appeler pour enrichir une base de données
            on_get_available_databases_callback: Fonction à appeler pour obtenir la liste des bases disponibles
            on_get_available_sources_callback: Fonction à appeler pour obtenir la liste des sources disponibles
        """
        # Dictionnaire des couleurs disponibles
        self.colors = {
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
        
        # Stockage des callbacks
        self.on_submit = on_submit_callback
        self.on_load_database = on_load_database_callback
        self.on_save_conversation = on_save_conversation_callback
        self.on_load_conversation = on_load_conversation_callback
        self.on_clear_conversation = on_clear_conversation_callback
        self.on_reset_history = on_reset_history_callback
        self.on_start_youtube_tool = on_start_youtube_tool_callback
        self.on_start_database_tool = on_start_database_tool_callback
        self.on_closing = on_closing_callback
        self.on_enrich_database = on_enrich_database_callback
        self.on_get_available_databases = on_get_available_databases_callback
        self.on_get_available_sources = on_get_available_sources_callback
        
        # Liste pour suivre les callbacks "after"
        self.after_ids = []
                
        # Drapeau indiquant si l'application est en cours de fermeture
        self.is_closing = False
        
        # Initialiser CustomTkinter
        ctk.set_appearance_mode("system")  # system, light, dark
        ctk.set_default_color_theme("blue")  # blue, green, dark-blue
        
        # Créer la fenêtre principale d'abord
        self.app = ctk.CTk()
        # Appliquer la police à tous les menus Tkinter
        menu_font = tkfont.Font(family="Arial", size=13)
        self.app.option_add("*Menu*Font", menu_font)
        self.app.title("Blow Chat YT - V 2.0 - By BlowCoder - 2025")
        self.app.geometry("1350x800")
        self.app.minsize(1350, 800)
        
        # Centrer la fenêtre
        width = 1350
        height = 800
        screen_width = self.app.winfo_screenwidth()
        screen_height = self.app.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.app.geometry(f"{width}x{height}+{x}+{y}")
        
        # Variables tkinter (APRÈS création de la fenêtre principale)
        self.theme_var = ctk.StringVar(value="blue")
        self.size_var = ctk.StringVar(value="19")
        self.color_system_var = ctk.StringVar(value='Bleu')
        self.color_user_var = ctk.StringVar(value='Vert')
        self.color_model_var = ctk.StringVar(value='Rouge')
        self.color_model_name_var = ctk.StringVar(value='Violet')
        self.color_user_name_var = ctk.StringVar(value='Orange')
        self.model_name_var = ctk.StringVar(value="LIHA")
        self.model_role_var = ctk.StringVar(value="Assistant")
        self.model_objective_var = ctk.StringVar(value="Aider les utilisateurs")
        self.youtube_api_key = ctk.StringVar()
        self.groq_api_key = ctk.StringVar()
        self.use_database = ctk.BooleanVar(value=False)
        self.speed_var = ctk.StringVar(value="Normal")
        self.huggingface_token = ctk.StringVar()
        
        # Variables pour les bases de données
        self.selected_database = ctk.StringVar(value="")  # Base sélectionnée
        self.new_database_name = ctk.StringVar(value="")  # Nom de la nouvelle base
        self.selected_source_folder = ctk.StringVar(value="3_transcriptions")  # Dossier source
        self.chunk_size_var = ctk.StringVar(value="500")  # Taille des chunks
        
        # Liste des modèles disponibles
        self.model_options = [
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "mistral-saba-24b",
            "qwen-qwq-32b",
        ]
        self.model_name = ctk.StringVar(value=self.model_options[0])
        
        # Continuer l'initialisation de l'interface
        self._create_menu()
        self._create_frames()
        self._create_tabs()
        self._create_left_sidebar()
        self._create_right_sidebar()
        self._create_assistant_tab()
        self._create_youtube_tab()
        self._create_database_tab()
        self._configure_text_tags()
        
        # Lier la touche Entrée au bouton Envoyer
        self.entry.bind("<Return>", self._on_submit_wrapper)
        
        # Gérer la fermeture de l'application
        self.app.protocol("WM_DELETE_WINDOW", self._on_closing_wrapper)
        
    def _create_menu(self):
        """Création de la barre de menu"""
        self.menu_bar = tk.Menu(self.app)
        
        # Menu Apparence
        appearance_menu = tk.Menu(self.menu_bar, tearoff=0)
        appearance_menu.add_command(label="Changer le thème", command=self.change_colors)
        appearance_menu.add_command(label="Changer la taille", command=self.change_font)
        appearance_menu.add_command(label="Personnaliser les couleurs", command=self.open_color_customization)
        self.menu_bar.add_cascade(label="Apparence", menu=appearance_menu)
        
        # Menu Paramètres
        settings_menu = tk.Menu(self.menu_bar, tearoff=0)
        settings_menu.add_command(label="Paramètres", command=self.open_settings)
        settings_menu.add_command(label="Assistant", command=self.open_assistant_settings)
        self.menu_bar.add_cascade(label="Paramètres", menu=settings_menu)
        
        # Menu Base de données
        database_menu = tk.Menu(self.menu_bar, tearoff=0)
        database_menu.add_command(label="Gestion des bases", command=self.open_database_management)
        database_menu.add_command(label="Ajouter un dossier source", command=self.add_source_folder)
        self.menu_bar.add_cascade(label="Bases de données", menu=database_menu)
        
        # Menu Aide
        help_menu = tk.Menu(self.menu_bar, tearoff=0)
        help_menu.add_command(label="GitHub", command=self.open_github)
        self.menu_bar.add_cascade(label="Aide", menu=help_menu)
        
        self.app.config(menu=self.menu_bar)
        
    def _create_frames(self):
        """Création des cadres principaux de l'interface"""
        # Sidebar gauche
        self.left_frame = ctk.CTkFrame(self.app, width=200)
        self.left_frame.pack(side="left", fill="y")
        
        # Sidebar droite
        self.right_frame = ctk.CTkFrame(self.app, width=200)
        self.right_frame.pack(side="right", fill="y")
        
        # Zone de contenu principal
        self.main_frame = ctk.CTkFrame(self.app)
        self.main_frame.pack(side="left", fill="both", expand=True)
        
    def _create_tabs(self):
        """Création des onglets dans le cadre principal"""
        self.notebook = ctk.CTkTabview(self.main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Créer les onglets
        self.assistant_tab = self.notebook.add("Assistant")
        self.youtube_tab = self.notebook.add("Outil YouTube")
        self.database_tab = self.notebook.add("Outil Base de Données")
        
    def _create_left_sidebar(self):
        """Création du contenu de la sidebar gauche"""
        # Base de données
        db_label = ctk.CTkLabel(self.left_frame, text="Choisir Base de Données puis charger DB:")
        db_label.pack(pady=5)
        
        # Dropdown pour sélectionner la base
        self.db_dropdown = ctk.CTkOptionMenu(
            self.left_frame,
            variable=self.selected_database,
            values=["Aucune base disponible"],
            dynamic_resizing=False,
            width=180
        )
        self.db_dropdown.pack(pady=5, padx=5)
        
        # Bouton pour charger la base sélectionnée
        load_db_button = ctk.CTkButton(self.left_frame, text="Charger DB", command=self.on_load_database)
        load_db_button.pack(pady=5, padx=5)
        
        # Sauvegarder
        save_label = ctk.CTkLabel(self.left_frame, text="Sauvegarder :")
        save_label.pack(pady=5)
        save_conv_button = ctk.CTkButton(self.left_frame, text="Sauvegarder Chat", command=self._save_conversation_wrapper)
        save_conv_button.pack(pady=5, padx=5)
        
        # Charger
        load_label = ctk.CTkLabel(self.left_frame, text="Charger :")
        load_label.pack(pady=5)
        load_conv_button = ctk.CTkButton(self.left_frame, text="Charger Chat", command=self._load_conversation_wrapper)
        load_conv_button.pack(pady=5, padx=5)
        
        # Effacer
        del_label = ctk.CTkLabel(self.left_frame, text="Effacer :")
        del_label.pack(pady=5)
        clear_conv_button = ctk.CTkButton(self.left_frame, text="Effacer Chat", command=self.on_clear_conversation)
        clear_conv_button.pack(pady=5, padx=5)
        
        # Réinitialiser
        reset_label = ctk.CTkLabel(self.left_frame, text="Réinitialiser :")
        reset_label.pack(pady=5)
        reset_history_button = ctk.CTkButton(self.left_frame, text="Réinitialiser Historique", command=self.on_reset_history)
        reset_history_button.pack(pady=5, padx=5)
        
    def _create_right_sidebar(self):
        """Création du contenu de la sidebar droite"""
        # Clés API
        param_label = ctk.CTkLabel(self.right_frame, text="Clés API :")
        param_label.pack(pady=5)
        settings_button = ctk.CTkButton(self.right_frame, text="Paramètres", command=self.open_settings)
        settings_button.pack(pady=5, padx=5)
        
        # Vitesse du streaming
        speed_label = ctk.CTkLabel(self.right_frame, text="Vitesse Stream :")
        speed_label.pack(pady=5)
        
        speed_options = ["Lent", "Normal", "Rapide", "Très Rapide", "Turbo"]
        speed_menu = ctk.CTkOptionMenu(self.right_frame, values=speed_options, variable=self.speed_var)
        speed_menu.pack(pady=5)
        
        # Modèle
        model_label = ctk.CTkLabel(self.right_frame, text="Modèles:")
        model_label.pack(pady=5)
        model_dropdown = ctk.CTkOptionMenu(self.right_frame, values=self.model_options, variable=self.model_name)
        model_dropdown.pack(pady=5)
        
        # Infos sur la base
        db_info_label = ctk.CTkLabel(self.right_frame, text="Infos Base de Données:")
        db_info_label.pack(pady=10)
        
        self.db_info_text = ctk.CTkTextbox(self.right_frame, height=200, width=180, font=("Arial", 15))
        self.db_info_text.pack(fill='x', padx=5, pady=5)
        self.db_info_text.configure(state="disabled")
        
        # Bouton d'information sur la base active
        info_button = ctk.CTkButton(self.right_frame, text="Infos Base Active", command=self.show_active_database_info)
        info_button.pack(padx=20)
        
    def _create_assistant_tab(self):
        """Création du contenu de l'onglet Assistant"""
        # Zone de texte pour afficher la conversation
        self.text_output = ctk.CTkTextbox(self.assistant_tab, wrap=tk.WORD)
        self.text_output.pack(fill='both', expand=True, pady=5)
        
        # Zone d'entrée pour la question
        input_frame = ctk.CTkFrame(self.assistant_tab)
        input_frame.pack(fill="x", pady=5)
        
        self.entry = ctk.CTkEntry(input_frame, width=700)
        self.entry.pack(side="left", fill="x", expand=True, padx=5)
        
        send_button = ctk.CTkButton(input_frame, text="Envoyer", command=self._on_submit_wrapper)
        send_button.pack(side="left", padx=5)
        
        # Case à cocher pour utiliser la base de données
        options_frame = ctk.CTkFrame(self.assistant_tab)
        options_frame.pack(fill="x", pady=5)
        
        use_db_checkbox = ctk.CTkCheckBox(options_frame, text="Cocher pour utiliser la base de données", variable=self.use_database)
        use_db_checkbox.pack(side="left", padx=20)
        
    def _create_youtube_tab(self):
        """Création du contenu de l'onglet Outil YouTube"""
        youtube_label = ctk.CTkLabel(self.youtube_tab, text="Outil de récupération d'informations et transcription YouTube")
        youtube_label.pack(pady=5)
        
        # Cadre pour les entrées
        input_frame = ctk.CTkFrame(self.youtube_tab)
        input_frame.pack(fill="x", pady=5, padx=10)
        
        # Colonne gauche
        left_column = ctk.CTkFrame(input_frame)
        left_column.pack(side="left", fill="y", expand=True, padx=10, pady=10)
        
        channel_id_label = ctk.CTkLabel(left_column, text="Nom ou ID de la chaîne YouTube:")
        channel_id_label.pack(pady=5, anchor="w")
        self.channel_id_entry = ctk.CTkEntry(left_column, width=300, placeholder_text="ex: @openiastudio")
        self.channel_id_entry.pack(pady=5, fill="x")
        
        video_ids_label = ctk.CTkLabel(left_column, text="IDs ou URLs des vidéos (séparés par des virgules) :")
        video_ids_label.pack(pady=5, anchor="w")
        self.video_ids_entry = ctk.CTkEntry(left_column, width=400, placeholder_text="ex: https://www.youtube.com/watch?v=Pzr_bc9OOFw&t=634s")
        self.video_ids_entry.pack(pady=5, fill="x")
        
        # Colonne droite
        right_column = ctk.CTkFrame(input_frame)
        right_column.pack(side="right", fill="y", expand=True, padx=10, pady=10)
        
        num_videos_label = ctk.CTkLabel(right_column, text="Nombre de vidéos à récupérer:")
        num_videos_label.pack(pady=5, anchor="w")
        self.num_videos_entry = ctk.CTkEntry(right_column, width=100)
        self.num_videos_entry.pack(pady=5, anchor="w")
        self.num_videos_entry.insert(0, "5")
        
        # Bouton de démarrage
        start_button = ctk.CTkButton(right_column, text="Démarrer", command=self._start_youtube_tool_wrapper)
        start_button.pack(pady=20)
        
        # Zone de sortie
        self.youtube_output = ctk.CTkTextbox(self.youtube_tab, font=("Arial", 19))
        self.youtube_output.pack(fill='both', expand=True, pady=5, padx=10)
        
    def _create_database_tab(self):
        """Création du contenu de l'onglet Outil Base de Données"""
        database_label = ctk.CTkLabel(self.database_tab, text="Outil pour transformer les textes en base de données vectorielle")
        database_label.pack(pady=5)
        
        # Cadre principal
        main_frame = ctk.CTkFrame(self.database_tab)
        main_frame.pack(fill="x", pady=5, padx=10)
        
        # Cadre pour la création de base
        create_frame = ctk.CTkFrame(main_frame)
        create_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        create_label = ctk.CTkLabel(create_frame, text="Créer une nouvelle base de données", font=("Arial", 14, "bold"))
        create_label.pack(pady=5)
        
        # Nom de la base
        db_name_label = ctk.CTkLabel(create_frame, text="Donner un nom à la base:")
        db_name_label.pack(pady=5, anchor="w")
        db_name_entry = ctk.CTkEntry(create_frame, textvariable=self.new_database_name, width=200)
        db_name_entry.pack(pady=5, fill="x")
        
        # Dossier source
        source_label = ctk.CTkLabel(create_frame, text="Choisir un dossier source \n ou ajouter via le menu Base de données:")
        source_label.pack(pady=5, anchor="w")
        
        # Obtenir la liste des sources disponibles
        source_folders = self.on_get_available_sources()
        if not source_folders:
            source_folders = ["3_transcriptions"]
        
        self.source_dropdown = ctk.CTkOptionMenu(
            create_frame,
            variable=self.selected_source_folder,
            values=source_folders,
            dynamic_resizing=False,
            width=200
        )
        self.source_dropdown.pack(pady=5, fill="x")
        
        # Taille des chunks
        chunk_size_label = ctk.CTkLabel(create_frame, text="Taille des chunks (caractères):")
        chunk_size_label.pack(pady=5, anchor="w")
        chunk_size_entry = ctk.CTkEntry(create_frame, textvariable=self.chunk_size_var, width=100)
        chunk_size_entry.pack(pady=5, anchor="w")
        
        # Bouton de création
        start_db_button = ctk.CTkButton(create_frame, text="Créer la base de données", command=self._start_database_tool_wrapper)
        start_db_button.pack(pady=10)
        
        # Cadre pour l'enrichissement
        enrich_frame = ctk.CTkFrame(main_frame)
        enrich_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        enrich_label = ctk.CTkLabel(enrich_frame, text="Enrichir une base existante", font=("Arial", 14, "bold"))
        enrich_label.pack(pady=5)
        
        # Base à enrichir (utilise la même variable que pour le chargement)
        enrich_db_label = ctk.CTkLabel(enrich_frame, text="Choisir une base à enrichir:")
        enrich_db_label.pack(pady=5, anchor="w")
        
        # Utiliser le même dropdown que dans la sidebar (mais avec un widget différent)
        enrich_db_dropdown = ctk.CTkOptionMenu(
            enrich_frame,
            variable=self.selected_database,
            values=["Aucune base disponible"],
            dynamic_resizing=False,
            width=200
        )
        enrich_db_dropdown.pack(pady=5, fill="x")
        
        # Bouton d'enrichissement
        enrich_button = ctk.CTkButton(enrich_frame, text="Enrichir la base", command=self._enrich_database_wrapper)
        enrich_button.pack(pady=10)
        
        # Zone de sortie
        self.database_output = ctk.CTkTextbox(self.database_tab, font=("Arial", 19))
        self.database_output.pack(fill='both', expand=True, pady=5, padx=10)
    
    def _configure_text_tags(self):
        """Configure les tags de couleur pour la zone de texte principale"""
        # Récupérer les couleurs depuis les variables StringVar
        def get_color_from_var(color_var):
            color_name = color_var.get()
            # Si le nom est dans le dictionnaire, utiliser sa valeur hexadécimale
            if color_name in self.colors:
                return self.colors[color_name]
            # Sinon, vérifier si c'est déjà un code hexadécimal valide
            elif re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_name):
                return color_name
            # Couleur par défaut si invalide
            else:
                print(f"Nom de couleur invalide: {color_name}, utilisation du noir par défaut")
                return '#000000'
        
        # Récupérer les couleurs pour chaque type de texte
        system_color = get_color_from_var(self.color_system_var)
        user_color = get_color_from_var(self.color_user_var)
        model_color = get_color_from_var(self.color_model_var)
        model_name_color = get_color_from_var(self.color_model_name_var)
        user_name_color = get_color_from_var(self.color_user_name_var)
        
        # Appliquer les couleurs aux tags
        self.text_output._textbox.tag_config('system', foreground=system_color)
        self.text_output._textbox.tag_config('user', foreground=user_color)
        self.text_output._textbox.tag_config('model', foreground=model_color)
        self.text_output._textbox.tag_config('model_name', foreground=model_name_color)
        self.text_output._textbox.tag_config('user_name', foreground=user_name_color)
        
        # Afficher les couleurs définies pour le débogage
        # print(f"Tags configurés avec les couleurs suivantes:")
        # print(f"- system: {system_color} (de {self.color_system_var.get()})")
        # print(f"- user: {user_color} (de {self.color_user_var.get()})")
        # print(f"- model: {model_color} (de {self.color_model_var.get()})")
        # print(f"- model_name: {model_name_color} (de {self.color_model_name_var.get()})")
        # print(f"- user_name: {user_name_color} (de {self.color_user_name_var.get()})")
    
    # Méthodes wrapper pour les callbacks
    def _on_submit_wrapper(self, event=None):
        """Wrapper pour le callback d'envoi de message"""
        query = self.entry.get()
        if not query.strip():  # Ne pas traiter les requêtes vides
            return
            
        self.on_submit(query, self.text_output, self.entry, self.model_name.get(), 
                      self.groq_api_key.get(), self.use_database.get(), self.speed_var.get(),
                      self.model_name_var.get())
    
    def _save_conversation_wrapper(self):
        """Wrapper pour le callback de sauvegarde de conversation"""
        file_path = filedialog.asksaveasfilename(defaultextension=".pkl", filetypes=[("Pickle Files", "*.pkl")])
        if file_path:
            self.on_save_conversation(file_path, self.text_output)
    
    def _load_conversation_wrapper(self):
        """Wrapper pour le callback de chargement de conversation"""
        file_path = filedialog.askopenfilename(filetypes=[("Pickle Files", "*.pkl")])
        if file_path:
            self.on_load_conversation(file_path, self.text_output)
    
    def _start_youtube_tool_wrapper(self):
        """Wrapper pour le callback de démarrage de l'outil YouTube"""
        channel_name = self.channel_id_entry.get()
        video_ids = self.video_ids_entry.get()
        num_videos = self.num_videos_entry.get()
        
        if not channel_name and not video_ids:
            messagebox.showerror("Erreur", "Veuillez fournir au moins un nom de chaîne ou des IDs de vidéos.")
            return
            
        self.on_start_youtube_tool(channel_name, video_ids, num_videos, 
                                  self.youtube_api_key.get(), self.youtube_output)
    
    def _start_database_tool_wrapper(self):
        """Wrapper pour le callback de démarrage de l'outil de base de données"""
        # Vérifier que le nom de la base est valide
        if not self.new_database_name.get().strip():
            messagebox.showerror("Erreur", "Veuillez spécifier un nom pour la nouvelle base de données.")
            return
            
        self.on_start_database_tool(self.database_output)
    
    def _enrich_database_wrapper(self):
        """Wrapper pour le callback d'enrichissement de base de données"""
        # Vérifier qu'une base est sélectionnée
        if not self.selected_database.get():
            messagebox.showerror("Erreur", "Veuillez sélectionner une base de données à enrichir.")
            return
            
        # Vérifier qu'un dossier source est sélectionné
        if not self.selected_source_folder.get():
            messagebox.showerror("Erreur", "Veuillez sélectionner un dossier source.")
            return
            
        self.on_enrich_database(self.database_output)
    
    def _on_closing_wrapper(self):
        """Wrapper pour le callback de fermeture de l'application avec gestion améliorée"""
        # Éviter les appels multiples pendant la fermeture
        if hasattr(self, '_is_closing_in_progress') and self._is_closing_in_progress:
            return
        self._is_closing_in_progress = True
            
        # Marquer l'application comme en cours de fermeture dès le début
        self.is_closing = True
        self.app._is_closing = True
        
        try:
            # Retirer le gestionnaire d'exceptions par défaut pour éviter les "bgerror"
            self.app.report_callback_exception = lambda *args: None
            
            # Supprimer les tâches planifiées en utilisant la commande Tcl
            try:
                self.app.tk.call('after', 'cancel', 'all')
            except Exception:
                pass
                
            # Méthode de secours: annuler aussi manuellement les after_ids
            for id in self.after_ids:
                try:
                    self.app.after_cancel(id)
                except Exception:
                    pass
            self.after_ids = []
            
            # Désactiver tous les "after" en remplaçant la méthode
            def disabled_after(*args, **kwargs):
                return None  # Ne rien faire
            self.app.after = disabled_after
            
            # Sauvegarde et autres opérations avant fermeture
            try:
                self.on_closing()
            except Exception as e:
                print(f"Erreur pendant la fermeture: {e}")
                
            # Détruire l'application sans attendre
            try:
                self.app.destroy()
            except Exception:
                pass
                
        finally:
            # S'assurer que l'application est terminée
            print("Application fermée avec succès.")
            # Forcer la sortie après un court délai si nécessaire
            if hasattr(sys, "exit"):
                try:
                    sys.exit(0)
                except Exception:
                    pass
    
    # Fonctions pour les dialogues et personnalisation
    def open_settings(self):
        """Ouvre la fenêtre des paramètres pour les clés API"""
        settings_window = ctk.CTkToplevel(self.app)
        settings_window.title("Paramètres")
        settings_window.geometry("400x300")
        settings_window.grab_set()  # Rendre la fenêtre modale
        
        youtube_api_label = ctk.CTkLabel(settings_window, text="YouTube API Key:")
        youtube_api_label.pack(pady=5)
        youtube_api_entry = ctk.CTkEntry(settings_window, width=300, textvariable=self.youtube_api_key)
        youtube_api_entry.pack(pady=5)
        
        groq_api_label = ctk.CTkLabel(settings_window, text="Groq API Key:")
        groq_api_label.pack(pady=5)
        groq_api_entry = ctk.CTkEntry(settings_window, width=300, textvariable=self.groq_api_key)
        groq_api_entry.pack(pady=5)
        
        # Ajout du champ pour le token Hugging Face
        hf_token_label = ctk.CTkLabel(settings_window, text="Hugging Face Token:")
        hf_token_label.pack(pady=5)
        
        # Créer la variable si elle n'existe pas
        if not hasattr(self, 'huggingface_token'):
            self.huggingface_token = tk.StringVar()
            # Charger la valeur depuis la configuration si disponible
            from app import BlowChatApp
            app_instance = BlowChatApp()
            self.huggingface_token.set(app_instance.config.get('API_KEYS', 'huggingface_token', fallback=''))
        
        hf_token_entry = ctk.CTkEntry(settings_window, width=300, textvariable=self.huggingface_token)
        hf_token_entry.pack(pady=5)
        
        def save_api_keys():
            # Sauvegarder le token Hugging Face dans la configuration
            from app import BlowChatApp
            app_instance = BlowChatApp()
            
            # Mettre à jour les clés API dans la configuration
            app_instance.update_config('API_KEYS', 'youtube_api_key', self.youtube_api_key.get())
            app_instance.update_config('API_KEYS', 'groq_api_key', self.groq_api_key.get())
            
            # Mettre à jour et réappliquer l'authentification Hugging Face
            app_instance.update_huggingface_token(self.huggingface_token.get())
            
            messagebox.showinfo("Succès", "Clés API sauvegardées avec succès.")
            settings_window.destroy()
        
        def reset_api_keys():
            self.youtube_api_key.set('')
            self.groq_api_key.set('')
            self.huggingface_token.set('')
        
        save_button = ctk.CTkButton(settings_window, text="Sauvegarder", command=save_api_keys)
        save_button.pack(pady=5)
        
        reset_button = ctk.CTkButton(settings_window, text="Réinitialiser", command=reset_api_keys)
        reset_button.pack(pady=5)
    
    def open_assistant_settings(self):
        """Ouvre la fenêtre des paramètres pour l'assistant"""
        assistant_window = ctk.CTkToplevel(self.app)
        assistant_window.title("Paramètres de l'assistant")
        assistant_window.geometry("400x300")
        assistant_window.grab_set()  # Rendre la fenêtre modale
        
        name_label = ctk.CTkLabel(assistant_window, text="Nom de l'assistant :")
        name_label.pack(pady=5)
        name_entry = ctk.CTkEntry(assistant_window, width=300, textvariable=self.model_name_var)
        name_entry.pack(pady=5)
        
        role_label = ctk.CTkLabel(assistant_window, text="Rôle de l'assistant :")
        role_label.pack(pady=5)
        role_entry = ctk.CTkEntry(assistant_window, width=300, textvariable=self.model_role_var)
        role_entry.pack(pady=5)
        
        objective_label = ctk.CTkLabel(assistant_window, text="Objectif de l'assistant :")
        objective_label.pack(pady=5)
        objective_entry = ctk.CTkEntry(assistant_window, width=300, textvariable=self.model_objective_var)
        objective_entry.pack(pady=5)
        
        def save_assistant_settings():
            messagebox.showinfo("Succès", "Paramètres de l'assistant sauvegardés avec succès.")
            assistant_window.destroy()
        
        save_button = ctk.CTkButton(assistant_window, text="Sauvegarder", command=save_assistant_settings)
        save_button.pack(pady=10)
    
    def open_database_management(self):
        """Ouvre la fenêtre de gestion des bases de données"""
        db_window = ctk.CTkToplevel(self.app)
        db_window.title("Gestion des bases de données")
        db_window.geometry("600x400")
        db_window.grab_set()  # Rendre la fenêtre modale
        
        # Cadre pour la liste des bases
        list_frame = ctk.CTkFrame(db_window)
        list_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        list_label = ctk.CTkLabel(list_frame, text="Bases de données disponibles", font=("Arial", 14, "bold"))
        list_label.pack(pady=5)
        
        # Obtenir la liste des bases
        available_dbs = self.on_get_available_databases()
        
        # Liste des bases
        db_listbox = tk.Listbox(list_frame, bg="#2b2b2b", fg="white", selectbackground="#4a4a4a", highlightthickness=0)
        db_listbox.pack(fill="both", expand=True, pady=5)
        
        for db in available_dbs:
            db_listbox.insert(tk.END, db)
        
        # Cadre pour les informations et actions
        info_frame = ctk.CTkFrame(db_window)
        info_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        info_label = ctk.CTkLabel(info_frame, text="Informations sur la base", font=("Arial", 14, "bold"))
        info_label.pack(pady=5)
        
        info_text = ctk.CTkTextbox(info_frame, height=200)
        info_text.pack(fill="both", expand=True, pady=5)
        
        # Fonction pour afficher les informations de la base sélectionnée
        def show_selected_db_info():
            selected_indices = db_listbox.curselection()
            if not selected_indices:
                return
                
            selected_db = db_listbox.get(selected_indices[0])
            # Appeler une fonction pour obtenir les informations de la base
            from app import \
                BlowChatApp  # Import local pour éviter l'import circulaire
            app_instance = BlowChatApp()
            db_info = app_instance.get_database_info(selected_db)
            
            # Afficher les informations
            info_text.delete("1.0", tk.END)
            if "error" in db_info:
                info_text.insert("1.0", f"Erreur: {db_info['error']}")
            else:
                info_text.insert("1.0", f"Nom: {db_info['name']}\n")
                info_text.insert(tk.END, f"Documents: {db_info.get('num_documents', 'Non disponible')}\n")
                info_text.insert(tk.END, f"Sources: {db_info.get('num_sources', 'Non disponible')}\n")
                info_text.insert(tk.END, f"Taille des chunks: {db_info.get('chunk_size', 'Non disponible')}\n")
                
                # Dates formatées
                import datetime
                if db_info.get('creation_date'):
                    creation_date = datetime.datetime.fromtimestamp(db_info['creation_date']).strftime('%Y-%m-%d %H:%M')
                    info_text.insert(tk.END, f"Création: {creation_date}\n")
                
                if db_info.get('last_modified'):
                    modified_date = datetime.datetime.fromtimestamp(db_info['last_modified']).strftime('%Y-%m-%d %H:%M')
                    info_text.insert(tk.END, f"Dernière modification: {modified_date}\n")
                
                info_text.insert(tk.END, f"Dossier source: {db_info.get('source_folder', 'Non spécifié')}\n")
        
        # Sélection dans la liste
        db_listbox.bind("<<ListboxSelect>>", lambda e: show_selected_db_info())
        
        # Boutons d'action
        buttons_frame = ctk.CTkFrame(info_frame)
        buttons_frame.pack(fill="x", pady=10)
        
        # Bouton pour charger la base sélectionnée
        def load_selected_db():
            selected_indices = db_listbox.curselection()
            if not selected_indices:
                messagebox.showerror("Erreur", "Aucune base sélectionnée.")
                return
                
            selected_db = db_listbox.get(selected_indices[0])
            self.selected_database.set(selected_db)
            self.on_load_database(selected_db)
            db_window.destroy()
        
        load_button = ctk.CTkButton(buttons_frame, text="Charger", command=load_selected_db)
        load_button.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        # Bouton pour supprimer la base sélectionnée
        def delete_selected_db():
            selected_indices = db_listbox.curselection()
            if not selected_indices:
                messagebox.showerror("Erreur", "Aucune base sélectionnée.")
                return
                
            selected_db = db_listbox.get(selected_indices[0])
            
            if messagebox.askyesno("Confirmation", f"Êtes-vous sûr de vouloir supprimer la base '{selected_db}' ?"):
                database_folder = "5_database"  # À remplacer par la configuration réelle
                
                # Supprimer les fichiers
                db_path = os.path.join(database_folder, f'{selected_db}.pkl')
                index_path = os.path.join(database_folder, f'faiss_index_{selected_db}.bin')
                
                try:
                    if os.path.exists(db_path):
                        os.remove(db_path)
                    if os.path.exists(index_path):
                        os.remove(index_path)
                        
                    messagebox.showinfo("Succès", f"La base '{selected_db}' a été supprimée.")
                    
                    # Mettre à jour la liste
                    db_listbox.delete(selected_indices[0])
                    info_text.delete("1.0", tk.END)
                    
                    # Mettre à jour les dropdowns
                    self.update_databases_dropdown(self.on_get_available_databases())
                    
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de la suppression : {e}")
        
        delete_button = ctk.CTkButton(buttons_frame, text="Supprimer", fg_color="#FF5555", hover_color="#FF0000", command=delete_selected_db)
        delete_button.pack(side="right", padx=5, pady=5, fill="x", expand=True)
    
    def add_source_folder(self):
        """Ouvre la fenêtre pour ajouter un dossier source personnalisé"""
        # Demander à l'utilisateur de sélectionner un dossier
        folder_path = filedialog.askdirectory(title="Sélectionner un dossier source")
        if not folder_path:
            return
            
        # Vérifier que le dossier existe
        if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            messagebox.showerror("Erreur", "Le dossier sélectionné n'existe pas.")
            return
            
        # Ajouter le dossier à la configuration
        # Cette partie nécessite une modification dans BlowChatApp pour stocker les dossiers dans la configuration
        # Pour l'instant, on se contente de mettre à jour le dropdown
        available_sources = self.on_get_available_sources()
        if folder_path not in available_sources:
            available_sources.append(folder_path)
            self.update_sources_dropdown(available_sources)
            messagebox.showinfo("Succès", f"Le dossier '{folder_path}' a été ajouté aux sources disponibles.")
            
            # Sélectionner automatiquement le nouveau dossier
            self.selected_source_folder.set(folder_path)
    
    def change_colors(self):
        """Ouvre la fenêtre pour changer les couleurs du thème"""
        colors_window = ctk.CTkToplevel(self.app)
        colors_window.title("Changer les couleurs")
        colors_window.geometry("300x300")
        colors_window.grab_set()  # Rendre la fenêtre modale
        
        theme_label = ctk.CTkLabel(colors_window, text="Sélectionner le thème:")
        theme_label.pack(pady=5)
        
        themes = ["blue", "green", "dark-blue"]
        
        def apply_theme():
            theme = self.theme_var.get()
            ctk.set_default_color_theme(theme)
            
            # Sauvegarder le thème dans la configuration
            import configparser
            config = configparser.ConfigParser()
            config.read("config.ini")
            
            if 'Appearance' not in config:
                config['Appearance'] = {}
            
            config['Appearance']['theme'] = theme
            
            # Écrire les modifications dans le fichier
            with open("config.ini", 'w') as f:
                config.write(f)
            
            messagebox.showinfo("Succès", f"Thème '{theme}' appliqué et sauvegardé.")
            colors_window.destroy()
        
        theme_dropdown = ctk.CTkOptionMenu(colors_window, values=themes, variable=self.theme_var)
        theme_dropdown.pack(pady=5)
        
        apply_button = ctk.CTkButton(colors_window, text="Appliquer", command=apply_theme)
        apply_button.pack(pady=5)
    
    def change_font(self):
        """Ouvre la fenêtre pour changer la taille de la police"""
        font_window = ctk.CTkToplevel(self.app)
        font_window.title("Changer la taille de la police")
        font_window.geometry("300x300")
        font_window.grab_set()  # Rendre la fenêtre modale
        
        size_label = ctk.CTkLabel(font_window, text="Sélectionner la taille de la police:")
        size_label.pack(pady=5)
        
        sizes = [str(s) for s in range(8, 25)]
        
        def apply_font():
            size = int(self.size_var.get())
            # Appliquer la taille de la police aux widgets
            new_font = ("Arial", size)
            self.text_output.configure(font=new_font)
            self.entry.configure(font=new_font)
            
            # Sauvegarder la taille de police dans la configuration
            import configparser
            config = configparser.ConfigParser()
            config.read("config.ini")
            
            if 'Appearance' not in config:
                config['Appearance'] = {}
            
            config['Appearance']['font_size'] = str(size)
            
            # Écrire les modifications dans le fichier
            with open("config.ini", 'w') as f:
                config.write(f)
            
            messagebox.showinfo("Succès", f"Police de taille {size} appliquée et sauvegardée.")
            font_window.destroy()
        
        size_dropdown = ctk.CTkOptionMenu(font_window, values=sizes, variable=self.size_var)
        size_dropdown.pack(pady=5)
        
        apply_button = ctk.CTkButton(font_window, text="Appliquer", command=apply_font)
        apply_button.pack(pady=5)
    
    def open_color_customization(self):
        """Ouvre la fenêtre pour personnaliser les couleurs des messages"""
        color_window = ctk.CTkToplevel(self.app)
        color_window.title("Personnaliser les couleurs")
        color_window.geometry("400x400")
        color_window.grab_set()  # Rendre la fenêtre modale
        
        # Listes des noms de couleurs pour les menus déroulants
        color_names = list(self.colors.keys())
        
        # Fonction pour créer une option de couleur
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
            color_hex = self.colors.get(color_var.get(), color_var.get())
            label.configure(bg_color=color_hex)
        
        # Créer les options pour chaque type de message
        create_color_option("Couleur des messages système :", self.color_system_var)
        create_color_option("Couleur des entrées utilisateur :", self.color_user_var)
        create_color_option("Couleur des réponses du modèle :", self.color_model_var)
        create_color_option("Couleur du nom du modèle :", self.color_model_name_var)
        create_color_option("Couleur du nom de l'utilisateur :", self.color_user_name_var)
        
        def apply_colors():
            # Fonction pour obtenir la valeur de couleur (code hexadécimal)
            def get_color_value(color_var):
                color_name = color_var.get()
                # Si le nom de couleur est dans le dictionnaire, obtenir le code hexadécimal
                # Sinon, vérifier si c'est un code hexadécimal valide, sinon utiliser une couleur par défaut
                if color_name in self.colors:
                    return self.colors.get(color_name)
                elif re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color_name):
                    return color_name
                else:
                    # Couleur par défaut si le nom n'est pas reconnu
                    print(f"Nom de couleur non reconnu: {color_name}, utilisation d'une couleur par défaut")
                    return '#000000'  # Noir par défaut
            
            try:
                # Obtenir les valeurs de couleur
                color_system = get_color_value(self.color_system_var)
                color_user = get_color_value(self.color_user_var)
                color_model = get_color_value(self.color_model_var)
                color_model_name = get_color_value(self.color_model_name_var)
                color_user_name = get_color_value(self.color_user_name_var)
                
                # Mettre à jour les tags avec les nouvelles couleurs
                self.text_output._textbox.tag_config('system', foreground=color_system)
                self.text_output._textbox.tag_config('user', foreground=color_user)
                self.text_output._textbox.tag_config('model', foreground=color_model)
                self.text_output._textbox.tag_config('model_name', foreground=color_model_name)
                self.text_output._textbox.tag_config('user_name', foreground=color_user_name)
                
                # IMPORTANT: Sauvegarder les couleurs dans le fichier de configuration
                # Pour cela, il faut accéder à l'instance de BlowChatApp
                from app import BlowChatApp
                app_instance = BlowChatApp.__new__(BlowChatApp)  # Crée une instance sans appeler __init__
                
                # Accéder à la configuration
                import configparser
                config = configparser.ConfigParser()
                config.read("config.ini")
                
                # Sauvegarder les nouvelles valeurs de couleur
                if 'Appearance' not in config:
                    config['Appearance'] = {}
                
                # S'assurer que nous utilisons les couleurs hexadécimales, pas les noms
                config['Appearance']['color_system'] = color_system
                config['Appearance']['color_user'] = color_user
                config['Appearance']['color_model'] = color_model
                config['Appearance']['color_model_name'] = color_model_name
                config['Appearance']['color_user_name'] = color_user_name
                
                # Vérifier que la valeur color_user_name est bien enregistrée
                print(f"Sauvegarde de color_user_name: {color_user_name}")
                
                # Écrire les modifications dans le fichier
                with open("config.ini", 'w') as f:
                    config.write(f)
                
                # Vérifier que les valeurs ont bien été écrites
                config_check = configparser.ConfigParser()
                config_check.read("config.ini")
                if 'Appearance' in config_check:
                    print(f"Valeur de color_user_name après sauvegarde: {config_check['Appearance'].get('color_user_name', 'Non définie')}")
                
                messagebox.showinfo("Succès", "Couleurs appliquées et sauvegardées.")
                color_window.destroy()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'application manuelle des couleurs: {e}")
        
        apply_button = ctk.CTkButton(color_window, text="Appliquer", command=apply_colors)
        apply_button.pack(pady=10)
    
    def update_conversation_display(self, conversation_history):
        """
        Met à jour l'affichage de la conversation à partir de l'historique
        
        Args:
            conversation_history: Liste des messages de la conversation
        """
        from langchain.schema import AIMessage, HumanMessage
        
        assistant_name = self.model_name_var.get()
        self.text_output._textbox.delete("1.0", ctk.END)
        
        for message in conversation_history:
            if isinstance(message, HumanMessage):
                # Afficher le message de l'utilisateur
                self.text_output._textbox.insert(ctk.END, "Boss: ", 'user_name')
                self.text_output._textbox.insert(ctk.END, f"{message.content}\n\n", 'user')
            elif isinstance(message, AIMessage):
                # Afficher la réponse de l'assistant
                self.text_output._textbox.insert(ctk.END, f"{assistant_name}: ", 'model_name')
                self.text_output._textbox.insert(ctk.END, f"{message.content}\n\n", 'model')
        
        self.text_output._textbox.see(ctk.END)
    
    def apply_config(self, theme, font_size):
        """
        Applique les paramètres de configuration chargés à l'interface
        
        Args:
            theme: Thème à appliquer
            font_size: Taille de la police à appliquer
        """
        # Appliquer le thème
        ctk.set_default_color_theme(theme)
        
        # Appliquer la taille de la police
        try:
            font_size = int(font_size)
        except ValueError:
            font_size = 12
            
        new_font = ("Arial", font_size)
        
        # Appliquer la nouvelle police aux widgets concernés
        self.text_output.configure(font=new_font)
        self.entry.configure(font=new_font)
    
    def log_info(self, message, text_widget=None):
        """
        Affiche un message d'information dans la zone de texte spécifiée
        
        Args:
            message: Message à afficher
            text_widget: Widget de texte où afficher le message
        """
        if text_widget:
            text_widget._textbox.insert(ctk.END, f"[INFO] {message}\n", 'system')
            text_widget._textbox.see(ctk.END)
        else:
            print(f"[INFO] {message}")
    
    def log_error(self, message, text_widget=None):
        """
        Affiche un message d'erreur dans la zone de texte spécifiée
        
        Args:
            message: Message à afficher
            text_widget: Widget de texte où afficher le message
        """
        if text_widget:
            text_widget._textbox.insert(ctk.END, f"[ERROR] {message}\n", 'system')
            text_widget._textbox.see(ctk.END)
        else:
            print(f"[ERROR] {message}")
    
    def update_databases_dropdown(self, databases):
        """
        Met à jour les menus déroulants des bases de données
        
        Args:
            databases: Liste des bases de données disponibles
        """
        if not databases:
            databases = ["Aucune base disponible"]
        
        # Mettre à jour le dropdown dans la sidebar
        self.db_dropdown.configure(values=databases)
        
        # Mettre à jour la variable si elle n'a pas de valeur valide
        if self.selected_database.get() not in databases:
            self.selected_database.set(databases[0])
            
        # Mettre à jour aussi le dropdown dans l'onglet Base de données
        # Rechercher tous les CTkOptionMenu dans l'interface
        for widget in self.database_tab.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                for sub_widget in widget.winfo_children():
                    if isinstance(sub_widget, ctk.CTkFrame):
                        for option_menu in sub_widget.winfo_children():
                            # Vérifier si c'est un menu déroulant utilisant
                            # selected_database
                            is_option_menu = isinstance(
                                option_menu, 
                                ctk.CTkOptionMenu
                            )
                            # Vérifier si ce menu utilise notre variable
                            if is_option_menu:
                                var = option_menu.cget("variable")
                                is_selected_db = var == self.selected_database
                            else:
                                is_selected_db = False
                            
                            if is_option_menu and is_selected_db:
                                option_menu.configure(values=databases)
    
    def update_sources_dropdown(self, sources):
        """
        Met à jour le menu déroulant des dossiers sources
        
        Args:
            sources: Liste des dossiers sources disponibles
        """
        if not sources:
            sources = ["3_transcriptions"]
        
        # Mettre à jour le dropdown
        self.source_dropdown.configure(values=sources)
        
        # Mettre à jour la variable si elle n'a pas de valeur valide
        if self.selected_source_folder.get() not in sources:
            self.selected_source_folder.set(sources[0])
    
    def show_active_database_info(self):
        """Affiche les informations sur la base de données active"""
        if not hasattr(self, 'db_info_text'):
            return
            
        # Vider le texte actuel
        self.db_info_text.configure(state="normal")
        self.db_info_text.delete("1.0", ctk.END)
        
        # Si aucune base n'est sélectionnée
        if not self.selected_database.get() or self.selected_database.get() == "Aucune base disponible":
            self.db_info_text.insert("1.0", "Aucune base de données active")
            self.db_info_text.configure(state="disabled")
            return
        
        # Récupérer les informations de la base
        from app import \
            BlowChatApp  # Import local pour éviter l'import circulaire
        app_instance = BlowChatApp()
        db_info = app_instance.get_database_info(self.selected_database.get())
        
        # Afficher les informations
        if "error" in db_info:
            self.db_info_text.insert("1.0", f"Erreur: {db_info['error']}")
        else:
            self.db_info_text.insert("1.0", f"Base active: {db_info['name']}\n")
            self.db_info_text.insert(ctk.END, f"Documents: {db_info.get('num_documents', 'N/A')}\n")
            self.db_info_text.insert(ctk.END, f"Sources: {db_info.get('num_sources', 'N/A')}\n")
            
            # Dates formatées
            import datetime
            if db_info.get('last_modified'):
                modified_date = datetime.datetime.fromtimestamp(db_info['last_modified']).strftime('%Y-%m-%d')
                self.db_info_text.insert(ctk.END, f"Modifiée: {modified_date}\n")
            
            if db_info.get('source_folder'):
                source = db_info['source_folder']
                # Tronquer si trop long
                if len(source) > 20:
                    source = source[:17] + "..."
                self.db_info_text.insert(ctk.END, f"Source: {source}")
        
        self.db_info_text.configure(state="disabled")
    
    def open_help(self):
        """Ouvre la fenêtre d'aide"""
        help_window = ctk.CTkToplevel(self.app)
        help_window.title("Aide")
        help_window.geometry("400x300")
        help_window.grab_set()  # Rendre la fenêtre modale
        
        help_text = ctk.CTkTextbox(help_window, height=200, width=300)
        help_text.pack(pady=5)
        
        # Ajouter le texte d'aide
        help_text.insert(ctk.END, "Cette section est en cours de développement. Veuillez revenir plus tard pour plus d'informations.")
    
    def open_github(self):
        """
        Ouvre la page GitHub du projet dans le navigateur par défaut.
        """
        url = "https://github.com/Blowdok/Blow-Chat-YT"
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le lien GitHub : {e}")
    
    def start(self):
        """Démarre la boucle principale de l'application avec gestion d'erreurs"""
        try:
            # Bloquer les signaux SIGINT (Ctrl+C) pour éviter les erreurs lors de la fermeture
            try:
                import signal
                signal.signal(signal.SIGINT, lambda sig, frame: self._on_closing_wrapper())
            except (ImportError, AttributeError):
                pass
                
            # Démarrer la boucle d'événements Tkinter avec gestion d'exceptions
            self.app.mainloop()
        except Exception as e:
            print(f"Erreur dans la boucle principale: {e}")
        finally:
            # Annuler tous les after planifiés pour éviter les erreurs bgerror
            try:
                # Utiliser la commande Tcl pour annuler tous les after
                self.app.tk.call('after', 'cancel', 'all')
            except Exception:
                pass
                
            # S'assurer que l'application est bien détruite même en cas d'erreur
            try:
                if self.app.winfo_exists():
                    self.app.destroy()
            except Exception:
                pass
                
            # print("Application fermée avec succès.")
    
    def get_app(self):
        """Retourne l'objet application principal"""
        return self.app