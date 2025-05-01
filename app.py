"""
Module app.py - Logique principale de l'application Blow Chat YT
Contient les classes et fonctions pour gérer la logique métier de l'application.
"""

import configparser
import math
import os
import pickle
import queue
import re
import sys
import threading
import tkinter as tk
from tkinter import messagebox
from urllib.parse import parse_qs, urlparse

import faiss
import PyPDF2
from googleapiclient.discovery import build
from huggingface_hub import login
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from sentence_transformers import SentenceTransformer
from youtube_transcript_api import YouTubeTranscriptApi

# Pour supprimer les messages d'erreur après la fermeture
try:
    original_displayerror = tk.Tk._report_exception
    
    def silent_error(self, *args):
        """Version silencieuse de _report_exception qui ignore les erreurs 'invalid command name'"""
        if len(args) >= 2 and isinstance(args[1], str) and "invalid command name" in args[1]:
            # Ignorer silencieusement cette erreur spécifique
            return
        # Pour toutes les autres erreurs, utiliser le gestionnaire original
        return original_displayerror(self, *args)
    
    # Appliquer le patch
    tk.Tk._report_exception = silent_error
except AttributeError:
    print("Attention: Impossible d'appliquer le patch pour les erreurs de fermeture")

# Méthode pour gérer les erreurs en arrière-plan
def custom_bg_error(app, error_msg, *args):
    """Gestionnaire d'erreurs personnalisé pour les erreurs en arrière-plan"""
    if "invalid command name" in error_msg or "application has been destroyed" in error_msg:
        # Ignorer les erreurs liées à la fermeture de l'application
        return
    # Sinon, afficher l'erreur
    print(f"Erreur en arrière-plan: {error_msg}")
    if hasattr(app, '_original_bgerror'):
        try:
            app._original_bgerror(error_msg, *args)
        except Exception:
            pass

# Méthode after originale et patch
original_after = tk.Misc.after

def patched_after(self, ms, func=None, *args):
    """Version modifiée de after qui ne programme pas de callbacks lors de la fermeture"""
    # Si nous sommes en cours de fermeture, ne rien faire
    if hasattr(self, '_is_closing') and self._is_closing:
        return None
        
    # Cas où after est utilisé comme sleep
    if func is None:
        return original_after(self, ms)
    
    # Pour les autres cas, wrapper la fonction comme avant
    def wrapped_func(*args):
        try:
            # Vérifier à nouveau l'état de fermeture au moment de l'exécution
            if hasattr(self, '_is_closing') and self._is_closing:
                return  # Ne rien faire si en cours de fermeture
            return func(*args)
        except (tk.TclError, Exception) as e:
            # Ignorer les erreurs de commande invalide et autres erreurs pendant la fermeture
            if not hasattr(self, '_is_closing') or not self._is_closing:
                print(f"Erreur ignorée dans un callback after: {str(e)}")
    
    # Stocker l'ID du callback pour pouvoir l'annuler plus tard
    after_id = original_after(self, ms, wrapped_func, *args)
    
    # Enregistrer l'ID si possible
    if hasattr(self, 'root') and hasattr(self.root, 'after_ids'):
        self.root.after_ids.append(after_id)
    elif hasattr(self, 'after_ids'):
        self.after_ids.append(after_id)
    
    return after_id

# Appliquer le patch
tk.Misc.after = patched_after

from interface import BlowChatInterface


class BlowChatApp:
    """Classe principale pour la logique métier de l'application Blow Chat YT"""
    
    def __init__(self):
        """Initialisation de l'application"""
        # Configuration
        self.config = configparser.ConfigParser()
        self.config_file = "config.ini"
        
        # Historique de conversation
        self.conversation_history = []
        
        # Index et données pour la recherche
        self.index = None
        self.data = None
        self.current_database_name = None
        
        # Créer les répertoires nécessaires
        self.create_directories()
        
        # Charger la configuration (UNE SEULE FOIS ICI)
        self.load_config()
        
        # Initialiser l'authentification Hugging Face
        self.init_huggingface_auth()
        
        # Initialiser l'interface
        self.init_interface()
        
    def init_huggingface_auth(self):
        """Initialise l'authentification avec Hugging Face Hub"""
        try:
            # D'abord vérifier les variables d'environnement
            hf_token = os.environ.get('HUGGINGFACE_TOKEN')
            
            # Si non trouvé, vérifier dans le fichier de configuration
            if not hf_token:
                hf_token = self.config.get('API_KEYS', 'huggingface_token', fallback='')
                
            # S'authentifier seulement si un token est disponible
            if hf_token:
                login(token=hf_token)
                print("Authentification Hugging Face réussie")
            else:
                print("Avertissement: Aucun token Hugging Face trouvé. Certaines fonctionnalités peuvent être limitées.")
                
        except Exception as e:
            import logging
            logging.getLogger('BlowChatYT').error(f"Erreur lors de l'initialisation de l'authentification Hugging Face: {e}")
            print(f"Erreur d'authentification Hugging Face: {e}")
    
    def create_directories(self):
        """Crée les répertoires nécessaires pour l'application"""
        directories = [
            "1_history_pkl",
            "2_conversation_txt",
            "3_transcriptions",
            "4_markdown_reports",
            "5_database"
        ]
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                print(f"Répertoire créé : {directory}")
    
    def load_config(self):
        """Charge la configuration depuis le fichier config.ini"""
        try:
            # Essayer de charger depuis le chemin par défaut
            if os.path.exists(self.config_file):
                self.config.read(self.config_file, encoding='utf-8')
                print(f"Configuration chargée depuis {self.config_file}")
            else:
                # Vérifier si une configuration existe dans le dossier utilisateur
                user_dir = os.path.expanduser("~")
                alt_config_file = os.path.join(user_dir, "blow_chat_config.ini")
                
                if os.path.exists(alt_config_file):
                    self.config_file = alt_config_file
                    self.config.read(self.config_file, encoding='utf-8')
                    print(f"Configuration chargée depuis le chemin alternatif: {self.config_file}")
                else:
                    # Créer une configuration par défaut
                    self._create_default_config()
                    print("Configuration par défaut créée")
        except Exception as e:
            print(f"Erreur lors du chargement de la configuration: {e}")
            # Créer une configuration par défaut en cas d'erreur
            self._create_default_config()
            print("Configuration par défaut créée suite à une erreur")
    
    def _create_default_config(self):
        """Crée une configuration par défaut"""
        self.config['API_KEYS'] = {}
        self.config['Appearance'] = {
            'theme': 'blue',
            'font_size': '12',
            'color_system': '#0000FF',
            'color_user': '#008000',
            'color_model': '#FF0000',
            'color_model_name': '#800080',
            'color_user_name': '#FFA500'
        }
        self.config['Assistant'] = {
            'name': 'LIHA',
            'role': 'Assistant',
            'objective': "Aider l'utilisateur"
        }
        self.config['Directories'] = {}
        self.config['Model'] = {
            'temperature': '0.3',
            'max_tokens': '6000',
            'max_history_length': '5'
        }
        self.config['Stream'] = {
            'default_speed': 'Normal',
            'lent': '1000',
            'normal': '500',
            'rapide': '100',
            'tres_rapide': '50',
            'turbo': '10'
        }
        self.save_config()
    
    def save_config(self):
        """Sauvegarde la configuration dans le fichier config.ini et retourne True si réussi"""
        try:
            # Vérifier les droits d'écriture en essayant d'écrire un fichier test
            test_file = os.path.join(os.path.dirname(self.config_file), "test_write.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except (IOError, PermissionError) as e:
                print(f"ATTENTION: Impossible d'écrire dans le répertoire: {e}")
                # Utiliser un chemin alternatif dans le dossier utilisateur
                user_dir = os.path.expanduser("~")
                self.config_file = os.path.join(user_dir, "blow_chat_config.ini")
                print(f"Utilisation du chemin alternatif pour la configuration: {self.config_file}")
            
            # Sauvegarde proprement dite
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            # print(f"Configuration sauvegardée dans {self.config_file}")
            return True
        except Exception as e:
            print(f"ERREUR CRITIQUE lors de la sauvegarde de la configuration: {e}")
            messagebox.showerror("Erreur de configuration", 
                               f"Impossible de sauvegarder la configuration: {e}\n"
                               "Vos paramètres ne seront pas conservés.")
            return False
    
    def init_interface(self):
        """Initialise l'interface graphique avec les callbacks nécessaires"""
        self.interface = BlowChatInterface(
            on_submit_callback=self.on_submit,
            on_load_database_callback=self.load_database,
            on_save_conversation_callback=self.save_conversation,
            on_load_conversation_callback=self.load_conversation,
            on_clear_conversation_callback=self.clear_conversation,
            on_reset_history_callback=self.reset_history,
            on_start_youtube_tool_callback=self.start_youtube_tool,
            on_start_database_tool_callback=self.start_database_tool,
            on_closing_callback=self.on_closing,
            on_enrich_database_callback=self.enrich_database,
            on_get_available_databases_callback=self.get_available_databases,
            on_get_available_sources_callback=self.get_available_sources
        )
        
        # S'assurer que la liste des callbacks after est initialisée
        if not hasattr(self.interface, 'after_ids'):
            self.interface.after_ids = []
        
        # Installer le gestionnaire d'erreurs personnalisé
        try:
            app_root = self.interface.app
            # Sauvegarder le gestionnaire d'erreurs d'origine
            app_root._original_bgerror = app_root.report_callback_exception
            # Installer notre gestionnaire personnalisé
            app_root.report_callback_exception = lambda *args: custom_bg_error(app_root, *args)
            
            # Configurer un gestionnaire d'erreurs spécifique au niveau Tcl pour les erreurs de commandes invalides
            app_root.tk.createcommand('::tkerror', lambda *args: None if 'invalid command name' in str(args) else None)
        except Exception as e:
            print(f"Erreur lors de l'installation du gestionnaire d'erreurs: {e}")
        
        # NE PAS recharger la configuration ici, elle est déjà chargée dans __init__
        
        # Mettre à jour la liste des bases de données disponibles
        self.update_database_list()
        
        # Mettre à jour la liste des sources disponibles
        self.update_source_list()
        
        # Appliquer la configuration à l'interface après l'initialisation
        self.apply_config_to_interface()
        
        # Charger l'historique de conversation
        self.load_history()
        
        # print("Interface initialisée avec succès et paramètres chargés depuis config.ini")
    
    def update_database_list(self):
        """Met à jour la liste des bases de données disponibles dans l'interface"""
        available_databases = self.get_available_databases()
        self.interface.update_databases_dropdown(available_databases)
    
    def update_source_list(self):
        """Met à jour la liste des sources disponibles dans l'interface"""
        available_sources = self.get_available_sources()
        self.interface.update_sources_dropdown(available_sources)
        
    def update_config(self, section, option, value):
        """
        Met à jour une option de configuration et la sauvegarde dans le fichier
        
        Args:
            section: Section de la configuration
            option: Option à mettre à jour
            value: Nouvelle valeur
        """
        try:
            # S'assurer que la section existe
            if section not in self.config:
                self.config[section] = {}
            
            # Convertir la valeur en chaîne si nécessaire
            str_value = str(value)
            
            # Vérifier si la valeur a changé pour éviter les sauvegardes inutiles
            if section in self.config and option in self.config[section] and self.config[section][option] == str_value:
                return  # Ne pas sauvegarder si la valeur n'a pas changé
            
            # Mettre à jour la valeur
            self.config[section][option] = str_value
            
            # Sauvegarder la configuration
            success = self.save_config()
            
            # Mettre à jour l'interface si nécessaire seulement si la sauvegarde a réussi
            if success and section == 'Appearance':
                if option == 'theme':
                    self.interface.theme_var.set(value)
                elif option == 'font_size':
                    self.interface.size_var.set(value)
                elif option.startswith('color_'):
                    # Mettre à jour les variables de couleur
                    if option == 'color_system':
                        self.interface.color_system_var.set(self.find_color_name(value))
                    elif option == 'color_user':
                        self.interface.color_user_var.set(self.find_color_name(value))
                    elif option == 'color_model':
                        self.interface.color_model_var.set(self.find_color_name(value))
                    elif option == 'color_model_name':
                        self.interface.color_model_name_var.set(self.find_color_name(value))
                    elif option == 'color_user_name':
                        self.interface.color_user_name_var.set(self.find_color_name(value))
                    
                    # Appliquer immédiatement les couleurs
                    self.manually_set_text_colors(
                        self.config.get('Appearance', 'color_system', fallback='#0000FF'),
                        self.config.get('Appearance', 'color_user', fallback='#008000'),
                        self.config.get('Appearance', 'color_model', fallback='#FF0000'),
                        self.config.get('Appearance', 'color_model_name', fallback='#800080'),
                        self.config.get('Appearance', 'color_user_name', fallback='#FFA500')
                    )
        except Exception as e:
            print(f"Erreur lors de la mise à jour de la configuration {section}.{option}: {e}")
            return False
    
    def apply_config_to_interface(self):
        """Applique la configuration chargée à l'interface"""
        # Initialiser d'abord les widgets avec les valeurs par défaut
        # pour s'assurer que tous les contrôles sont créés
        self.interface.apply_config('blue', '13')
        
        # Charger les paramètres d'apparence
        theme = self.config.get('Appearance', 'theme', fallback='blue')
        font_size = self.config.get('Appearance', 'font_size', fallback='13')
        
        # Charger les couleurs des messages
        color_system = self.config.get('Appearance', 'color_system', fallback='#0000FF')
        color_user = self.config.get('Appearance', 'color_user', fallback='#008000')
        color_model = self.config.get('Appearance', 'color_model', fallback='#FF0000')
        color_model_name = self.config.get('Appearance', 'color_model_name', fallback='#800080')
        color_user_name = self.config.get('Appearance', 'color_user_name', fallback='#FFA500')
        
        # print(f"Lecture des couleurs depuis la config:")
        # print(f"- color_system: {color_system}")
        # print(f"- color_user: {color_user}")
        # print(f"- color_model: {color_model}")
        # print(f"- color_model_name: {color_model_name}")
        # print(f"- color_user_name: {color_user_name}")
        
        # S'assurer que les couleurs chargées sont valides
        color_system = self.ensure_valid_color(color_system, '#0000FF')
        color_user = self.ensure_valid_color(color_user, '#008000')
        color_model = self.ensure_valid_color(color_model, '#FF0000')
        color_model_name = self.ensure_valid_color(color_model_name, '#800080')
        color_user_name = self.ensure_valid_color(color_user_name, '#FFA500')
        
        # Directement définir les variables de couleur de l'interface avec les codes hexadécimaux
        self.interface.color_system_var.set(self.find_color_name(color_system))
        self.interface.color_user_var.set(self.find_color_name(color_user))
        self.interface.color_model_var.set(self.find_color_name(color_model))
        self.interface.color_model_name_var.set(self.find_color_name(color_model_name))
        self.interface.color_user_name_var.set(self.find_color_name(color_user_name))
        
        # print(f"Variables de couleur définies:")
        # print(f"- color_system_var: {self.interface.color_system_var.get()}")
        # print(f"- color_user_var: {self.interface.color_user_var.get()}")
        # print(f"- color_model_var: {self.interface.color_model_var.get()}")
        # print(f"- color_model_name_var: {self.interface.color_model_name_var.get()}")
        # print(f"- color_user_name_var: {self.interface.color_user_name_var.get()}")
        
        # Définir les variables de theme et taille
        self.interface.theme_var.set(theme)
        self.interface.size_var.set(font_size)
        
        # Charger les clés API
        youtube_api_key = self.config.get('API_KEYS', 'youtube_api_key', fallback='')
        groq_api_key = self.config.get('API_KEYS', 'groq_api_key', fallback='')
        self.interface.youtube_api_key.set(youtube_api_key)
        self.interface.groq_api_key.set(groq_api_key)
        
        # Charger les paramètres de l'assistant
        model_name = self.config.get('Assistant', 'name', fallback='LIHA')
        model_role = self.config.get('Assistant', 'role', fallback='Assistant')
        model_objective = self.config.get('Assistant', 'objective', fallback="Aider l'utilisateur")
        self.interface.model_name_var.set(model_name)
        self.interface.model_role_var.set(model_role)
        self.interface.model_objective_var.set(model_objective)
        
        # Appliquer maintenant les paramètres de theme et taille d'affichage
        self.interface.apply_config(theme, font_size)
        
        # Définir explicitement les couleurs dans l'interface Tkinter
        self.manually_set_text_colors(
            color_system, color_user, color_model, color_model_name, color_user_name
        )
        
        # Vitesse de streaming par défaut
        default_speed = self.config.get('Stream', 'default_speed', fallback='Normal')
        self.interface.speed_var.set(default_speed)
    
    def ensure_valid_color(self, color, default_color):
        """Vérifie si une couleur est valide et retourne une valeur par défaut si nécessaire"""
        if not color or not isinstance(color, str) or not color.startswith('#'):
            return default_color
        
        # Vérifier la longueur (format #RRGGBB)
        if len(color) != 7:
            return default_color
            
        # Vérifier que c'est un code hexadécimal valide
        try:
            int(color[1:], 16)
            return color
        except ValueError:
            return default_color
    
    def manually_set_text_colors(self, system_color, user_color, model_color, 
                                model_name_color, user_name_color):
        """Applique manuellement les couleurs au widget de texte"""
        try:
            textbox = self.interface.text_output._textbox
            
            # Définir les couleurs des tags
            textbox.tag_configure('system', foreground=system_color)
            textbox.tag_configure('user', foreground=user_color)
            textbox.tag_configure('model', foreground=model_color)
            textbox.tag_configure('model_name', foreground=model_name_color)
            textbox.tag_configure('user_name', foreground=user_name_color)
            
            # Forcer une mise à jour
            textbox.update()
        except Exception as e:
            print(f"Erreur lors de l'application manuelle des couleurs: {e}")
    
    def find_color_name(self, hex_code):
        """Trouve le nom d'une couleur à partir de son code hexadécimal"""
        for name, value in self.interface.colors.items():
            if value.lower() == hex_code.lower():
                return name
        # Si la couleur n'est pas trouvée, retourner directement le code hexadécimal
        return hex_code
    
    def save_history(self):
        """Sauvegarde l'historique de conversation et la configuration"""
        history_folder = "1_history_pkl"
        history_files = os.path.join(history_folder, "memo.pkl")
        try:
            with open(history_files, 'wb') as f:
                pickle.dump(self.conversation_history, f)
            # print("Historique de conversation sauvegardé automatiquement.")
            
            # Sauvegarder également la configuration
            self.save_config()
            print("Historique et configuration sauvegardée automatiquement.")
            
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de l'historique : {e}")
    
    def load_history(self):
        """Charge l'historique de conversation"""
        history_folder = "1_history_pkl"
        history_files = os.path.join(history_folder, "memo.pkl")
        if os.path.exists(history_files):
            try:
                with open(history_files, 'rb') as f:
                    self.conversation_history = pickle.load(f)
                # print("Historique de conversation chargé automatiquement.")
                # Mettre à jour l'interface utilisateur
                self.interface.update_conversation_display(self.conversation_history)
            except Exception as e:
                print(f"Erreur lors du chargement de l'historique : {e}")
        else:
            self.conversation_history = []
    
    def reset_history(self):
        """Réinitialise l'historique de conversation"""
        self.conversation_history = []
        # Supprimer le fichier d'historique
        history_folder = "1_history_pkl"
        history_files = os.path.join(history_folder, "memo.pkl")
        if os.path.exists(history_files):
            os.remove(history_files)
        self.interface.update_conversation_display(self.conversation_history)
        messagebox.showinfo("Information", "L'historique de conversation a été réinitialisé.")
        
    def save_conversation(self, file_path, text_widget):
        """Sauvegarde la conversation dans un fichier"""
        try:
            with open(file_path, 'wb') as f:
                pickle.dump({
                    'text': text_widget._textbox.get("1.0", "end"),
                    'history': self.conversation_history
                }, f)
            messagebox.showinfo("Succès", "Conversation sauvegardée avec succès.")
        except Exception as e:
            self.interface.log_error(f"Erreur lors de la sauvegarde de la conversation : {e}", text_widget)
    
    def load_conversation(self, file_path, text_widget):
        """Charge une conversation depuis un fichier"""
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            text_widget._textbox.delete("1.0", "end")
            text_widget._textbox.insert("1.0", data['text'])
            self.conversation_history = data.get('history', [])
            messagebox.showinfo("Succès", "Conversation chargée avec succès.")
        except Exception as e:
            self.interface.log_error(f"Erreur lors du chargement de la conversation : {e}", text_widget)
    
    def clear_conversation(self):
        """Efface le contenu de la zone de conversation"""
        self.interface.text_output._textbox.delete("1.0", "end")
        # Ne pas effacer self.conversation_history pour préserver l'historique
    
    def save_interface_settings_to_config(self):
        """Sauvegarde tous les paramètres actuels de l'interface dans le fichier de configuration"""
        try:
            # Sauvegarder les paramètres d'apparence
            self.update_config('Appearance', 'theme', self.interface.theme_var.get())
            self.update_config('Appearance', 'font_size', self.interface.size_var.get())
            
            # Récupérer les couleurs actuelles depuis l'interface
            # Plutôt que d'utiliser le dictionnaire self.interface.colors qui peut ne pas contenir la couleur,
            # on utilise directement les valeurs des variables pour être sûr d'avoir les bonnes couleurs
            colors = {}
            
            # Pour la couleur système
            color_system_name = self.interface.color_system_var.get()
            if color_system_name in self.interface.colors:
                colors['color_system'] = self.interface.colors[color_system_name]
            else:
                colors['color_system'] = '#0000FF'  # Bleu par défaut
                
            # Pour la couleur utilisateur
            color_user_name = self.interface.color_user_var.get()
            if color_user_name in self.interface.colors:
                colors['color_user'] = self.interface.colors[color_user_name]
            else:
                colors['color_user'] = '#008000'  # Vert par défaut
                
            # Pour la couleur du modèle
            color_model_name = self.interface.color_model_var.get()
            if color_model_name in self.interface.colors:
                colors['color_model'] = self.interface.colors[color_model_name]
            else:
                colors['color_model'] = '#FF0000'  # Rouge par défaut
                
            # Pour la couleur du nom du modèle
            color_model_name_name = self.interface.color_model_name_var.get()
            if color_model_name_name in self.interface.colors:
                colors['color_model_name'] = self.interface.colors[color_model_name_name]
            else:
                colors['color_model_name'] = '#800080'  # Violet par défaut
                
            # Pour la couleur du nom de l'utilisateur
            color_user_name_name = self.interface.color_user_name_var.get()
            if color_user_name_name in self.interface.colors:
                colors['color_user_name'] = self.interface.colors[color_user_name_name]
            else:
                colors['color_user_name'] = '#FFA500'  # Orange par défaut
            
            # Vérifier et corriger les couleurs si elles sont vides ou None
            for color_key, color_value in colors.items():
                if not color_value:
                    # Utiliser une valeur par défaut si la couleur est vide
                    if color_key == 'color_system':
                        colors[color_key] = '#0000FF'  # Bleu par défaut
                    elif color_key == 'color_user':
                        colors[color_key] = '#008000'  # Vert par défaut
                    elif color_key == 'color_model':
                        colors[color_key] = '#FF0000'  # Rouge par défaut
                    elif color_key == 'color_model_name':
                        colors[color_key] = '#800080'  # Violet par défaut
                    elif color_key == 'color_user_name':
                        colors[color_key] = '#FFA500'  # Orange par défaut
            
            # Debug pour vérifier les valeurs qui vont être sauvegardées
            # print("Couleurs à sauvegarder:")
            #for color_key, color_value in colors.items():
            #    print(f"  {color_key} = {color_value}")
            
            # Sauvegarder les couleurs validées
            for color_key, color_value in colors.items():
                self.update_config('Appearance', color_key, color_value)
            
            # Sauvegarder les clés API
            self.update_config('API_KEYS', 'youtube_api_key', self.interface.youtube_api_key.get())
            self.update_config('API_KEYS', 'groq_api_key', self.interface.groq_api_key.get())
            
            # Sauvegarder les paramètres de l'assistant
            self.update_config('Assistant', 'name', self.interface.model_name_var.get())
            self.update_config('Assistant', 'role', self.interface.model_role_var.get())
            self.update_config('Assistant', 'objective', self.interface.model_objective_var.get())
            
            # Sauvegarder les vitesses de streaming
            self.update_config('Stream', 'default_speed', self.interface.speed_var.get())
            
            # Vérifier que la configuration a bien été sauvegardée
            self.config.read(self.config_file, encoding='utf-8')
            if 'Appearance' in self.config:
                for color_key in colors.keys():
                    saved_value = self.config['Appearance'].get(color_key, "Non trouvé")
                    # print(f"Valeur sauvegardée pour {color_key}: {saved_value}")
            
            # print("Paramètres de l'application sauvegardés dans config.ini")
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des paramètres : {e}")

    def on_closing(self):
        """Opérations à effectuer lors de la fermeture de l'application"""
        print("Début de la fermeture de l'application...")
        
        # Empêcher des appels multiples à cette fonction
        if hasattr(self, '_closing_in_progress') and self._closing_in_progress:
            return
        self._closing_in_progress = True
        
        # Sauvegarder les paramètres de l'interface AVANT de marquer l'application comme en cours de fermeture
        self.save_interface_settings_to_config()
        
        # Marquer l'interface comme en cours de fermeture
        self.interface.is_closing = True
        
        # Désactiver la gestion d'erreurs pour éviter les messages après fermeture
        try:
            self.interface.app.report_callback_exception = lambda *args: None
        except Exception:
            pass
        
        # Annuler tous les scripts 'after' avec la commande Tcl
        try:
            self.interface.app.tk.call('after', 'cancel', 'all')
        except Exception:
            pass
            
        # Annuler tous les callbacks en attente de manière individuelle
        try:
            for after_id in self.interface.after_ids:
                try:
                    self.interface.app.after_cancel(after_id)
                except Exception:
                    pass  # Ignorer les erreurs lors de l'annulation
            
            # Vider la liste des callbacks
            self.interface.after_ids = []
        except Exception:
            pass  # Ignorer les erreurs
        
        # Sauvegarder l'historique
        try:
            self.save_history()
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de l'historique: {e}")
        
        print("Fermeture de l'application terminée.")
    
    def on_submit(self, query, text_widget, entry_widget, model_name, groq_api_key, use_database, speed, assistant_name):
        """Gère l'envoi d'un message par l'utilisateur"""
        if query.lower() == 'exit':
            self.interface.app.destroy()
            return
        
        # Effacer le champ de saisie
        entry_widget.delete(0, "end")
        
        # Insérer le nom de l'utilisateur
        text_widget._textbox.insert("end", "Boss: ", 'user_name')
        # Insérer la question de l'utilisateur
        text_widget._textbox.insert("end", f"{query}\n\n", 'user')
        text_widget._textbox.see("end")
        
        # Ajouter le message de l'utilisateur à l'historique
        self.conversation_history.append(HumanMessage(content=query))
        
        # Obtenir le contexte si la base de données est utilisée
        context = ''
        if use_database:
            if self.index is None or self.data is None:
                text_widget._textbox.insert("end", "La base de données n'est pas chargée. Veuillez la charger d'abord.\n", 'system')
                context = ''
            else:
                try:
                    # Recherche dans la base de données
                    documents = self.search_documents(query, self.index, self.data, top_k=5, max_context_length=3000)
                    context = "\n".join(documents)
                except Exception as e:
                    text_widget._textbox.insert("end", f"Erreur lors de la recherche dans la base de données : {e}\n", 'system')
        
        # Appeler generate_answer
        self.generate_answer(query, context, text_widget, model_name, groq_api_key, speed, assistant_name)
    
    def generate_answer(self, query, context, text_widget, model_name, groq_api_key, speed, assistant_name):
        """Génère une réponse du modèle"""
        q = queue.Queue()
        
        def insert_text():
            """Fonction pour insérer le texte dans l'interface au fur et à mesure"""
            try:
                while True:
                    text, tag = q.get_nowait()
                    if text:
                        text_widget._textbox.insert("end", text, tag)
                        text_widget._textbox.see("end")
                        text_widget._textbox.update_idletasks()
            except queue.Empty:
                pass
            finally:
                if thread.is_alive() and not self.interface.is_closing:
                    # Déterminer l'intervalle en fonction de la vitesse
                    interval_map = {
                        "Lent": int(self.config.get('Stream', 'lent', fallback='1000')),
                        "Normal": int(self.config.get('Stream', 'normal', fallback='500')),
                        "Rapide": int(self.config.get('Stream', 'rapide', fallback='100')),
                        "Très Rapide": int(self.config.get('Stream', 'tres_rapide', fallback='50')),
                        "Turbo": int(self.config.get('Stream', 'turbo', fallback='10'))
                    }
                    interval = interval_map.get(speed, 500)
                    after_id = text_widget.after(interval, insert_text)
                    # Ajouter l'ID à la liste des callbacks
                    self.interface.after_ids.append(after_id)
        
        def run_model():
            """Fonction pour exécuter le modèle dans un thread séparé"""
            if not groq_api_key:
                q.put(("La clé API Groq n'a pas été fournie.\n\n", 'system'))
                return
            
            os.environ['GROQ_API_KEY'] = groq_api_key
            
            # Construire les messages en incluant l'historique
            messages = []
            
            # Ajouter le message système initial avec le rôle et l'objectif
            assistant_role = self.interface.model_role_var.get()
            assistant_objective = self.interface.model_objective_var.get()
            system_prompt = f"{assistant_name}. Tu es {assistant_role}. Ton objectif est : {assistant_objective}."
            
            # Ajouter le nom de la base de données si elle est chargée
            if self.current_database_name and context:
                system_prompt += f"\n\nJe consulte pour toi la base de données '{self.current_database_name}'."
                
            if context:
                system_prompt += f"\n\nContexte :\n{context}"
            
            messages.append(SystemMessage(content=system_prompt))
            
            # Vérifier la taille du system_prompt
            token_count = self.count_tokens(system_prompt)
            if token_count > 18000:
                q.put(("\nLe contexte est trop volumineux pour le modèle. Veuillez réduire la taille du contexte.\n", 'system'))
                return
            
            # Ajouter l'historique de la conversation
            messages.extend(self.conversation_history)
            
            try:
                # Paramètres du modèle depuis la configuration
                temperature = float(self.config.get('Model', 'temperature', fallback='0.3'))
                max_tokens = int(self.config.get('Model', 'max_tokens', fallback='6000'))
                
                llm = ChatGroq(
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=None,
                    max_retries=2,
                    streaming=True,  # Activer le streaming
                )
                
                # Insérer le nom du modèle avec le tag 'model_name'
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
                self.conversation_history.append(AIMessage(content=response_content))
                
                # Limiter la taille de l'historique si nécessaire
                max_history_length = int(self.config.get('Model', 'max_history_length', fallback='5'))
                if len(self.conversation_history) > max_history_length * 2:
                    # Supprimer les messages les plus anciens
                    self.conversation_history[:] = self.conversation_history[-max_history_length*2:]
                
            except Exception as e:
                q.put((f"\nErreur lors de l'appel à Groq : {e}\n\n", 'system'))
        
        thread = threading.Thread(target=run_model)
        thread.start()
        
        text_widget.after(100, insert_text)
    
    def count_tokens(self, text):
        """
        Compte approximativement le nombre de tokens dans le texte
        Un token correspond à environ 4 caractères en moyenne
        """
        return len(text) // 4
    
    def get_available_databases(self):
        """
        Récupère la liste des bases de données vectorielles disponibles
        
        Returns:
            list: Liste des noms de bases disponibles
        """
        database_folder = self.config.get('Directories', 'database', fallback='5_database')
        available_dbs = []
        
        try:
            # Parcourir tous les fichiers du dossier
            for file in os.listdir(database_folder):
                # Ne considérer que les fichiers .pkl qui ne commencent pas par 'faiss_index_'
                if file.endswith('.pkl') and not file.startswith('faiss_index_'):
                    # Extraire le nom de la base (sans l'extension .pkl)
                    db_name = os.path.splitext(file)[0]
                    # Vérifier que le fichier d'index correspondant existe
                    if os.path.exists(os.path.join(database_folder, f'faiss_index_{db_name}.bin')):
                        available_dbs.append(db_name)
        except Exception as e:
            print(f"Erreur lors de la recherche des bases disponibles : {e}")
        
        return available_dbs
    
    def get_available_sources(self):
        """
        Récupère la liste des dossiers source disponibles pour créer des bases
        
        Returns:
            list: Liste des dossiers disponibles
        """
        # Dossiers sources par défaut
        default_sources = [
            "3_transcriptions",
            "4_markdown_reports"
        ]
        
        # Ajouter les dossiers personnalisés depuis la configuration
        custom_sources = []
        if 'Sources' in self.config:
            for key, value in self.config['Sources'].items():
                if os.path.exists(value) and value not in default_sources:
                    custom_sources.append(value)
        
        # Combiner les sources et vérifier leur existence
        available_sources = []
        for source in default_sources + custom_sources:
            if os.path.exists(source) and os.path.isdir(source):
                available_sources.append(source)
        
        return available_sources
    
    def load_database(self, database_name=None):
        """
        Charge une base de données vectorielle spécifique
        
        Args:
            database_name: Nom de la base à charger (si None, utilise celle sélectionnée dans l'interface)
        """
        if database_name is None:
            database_name = self.interface.selected_database.get()
        
        if not database_name:
            messagebox.showerror("Erreur", "Aucune base de données sélectionnée.")
            return
        
        try:
            self.index, self.data = self.load_vector_database(database_name)
            self.current_database_name = database_name
            self.interface.use_database.set(True)
            messagebox.showinfo("Succès", f"Base de données '{database_name}' chargée avec succès.")
        except Exception as e:
            self.interface.log_error(f"Erreur lors du chargement de la base de données '{database_name}' : {e}", self.interface.text_output)
            self.interface.use_database.set(False)
            messagebox.showerror("Erreur", f"Erreur lors du chargement de la base de données : {e}")
    
    def load_vector_database(self, db_name):
        """
        Charge une base de données vectorielle.
        
        Args:
            db_name: Nom de la base de données à charger
            
        Returns:
            Tuple (index, data) ou None en cas d'erreur
        """
        try:
            # Vérifier que la base existe
            database_folder = self.config.get('Directories', 'database', fallback='5_database')
            db_path = os.path.join(database_folder, f'{db_name}.pkl')
            index_path = os.path.join(database_folder, f'faiss_index_{db_name}.bin')
            
            if not os.path.exists(db_path) or not os.path.exists(index_path):
                print(f"La base de données '{db_name}' n'existe pas")
                return None
            
            # Charger les données
            with open(db_path, 'rb') as f:
                data = pickle.load(f)
            
            # Charger l'index FAISS
            index = faiss.read_index(index_path)
            
            # S'assurer que le modèle SentenceTransformer est disponible
            # (nécessaire pour les recherches futures)
            model_name = 'sentence-transformers/all-MiniLM-L6-v2'
            try:
                model = SentenceTransformer(model_name)
                print(f"Modèle {model_name} chargé avec succès pour la recherche")
            except Exception as e:
                import logging
                logging.getLogger('BlowChatYT').error(f"Erreur lors de l'initialisation du service d'embeddings pour la recherche: {e}")
                print(f"Attention: Impossible de charger le modèle SentenceTransformer. Les recherches pourraient ne pas fonctionner correctement. Erreur: {e}")
            
            return index, data
        except Exception as e:
            import logging
            logging.getLogger('BlowChatYT').error(f"Erreur lors du chargement de la base de données: {e}")
            print(f"Erreur lors du chargement de la base de données '{db_name}': {e}")
            return None
    
    def search_documents(self, query, index, data, top_k=10, max_context_length=4000):
        """
        Recherche les documents les plus pertinents pour une requête donnée.
        Limite la longueur totale du contexte.
        
        Args:
            query: Requête de recherche
            index: Index FAISS à utiliser
            data: Données des documents
            top_k: Nombre maximal de résultats à retourner
            max_context_length: Longueur maximale totale du contexte
            
        Returns:
            list: Liste des documents pertinents
        """
        # Encoder la requête
        model = SentenceTransformer('all-MiniLM-L6-v2')
        query_vector = model.encode([query])
        
        # Recherche dans l'index
        distances, indices = index.search(query_vector, top_k * 2)  # Obtenir plus de résultats pour filtrer ensuite
        
        results = []
        total_length = 0
        
        # Ajouter des informations de source pour chaque document
        for i, idx in enumerate(indices[0]):
            if idx < len(data['documents']):
                document = data['documents'][idx]
                
                # Ajouter des métadonnées si disponibles
                if 'metadata' in data and idx < len(data['metadata']):
                    metadata = data['metadata'][idx]
                    source_info = f"\n[Source: {metadata.get('filename', 'inconnu')}]"
                elif 'filenames' in data and idx < len(data['filenames']):
                    source_info = f"\n[Source: {data['filenames'][idx]}]"
                else:
                    source_info = ""
                
                # Ajouter le score de similarité avec gestion des cas anormaux
                distance = distances[0][i]
                # Vérification de la validité de la distance (ni infini, ni NaN)
                if not math.isfinite(distance):
                    # Log pour le debug si la distance est invalide
                    print(
                        f"Distance invalide détectée à l'index {i}: {distance}"
                    )
                    similarity = "\n[Pertinence: valeur de distance invalide]"
                else:
                    # On borne la distance pour éviter l'overflow et garantir un pourcentage cohérent
                    distance = min(max(distance, 0.0), 1.0)
                    similarity = (
                        f"\n[Pertinence: {100 * (1 - distance):.1f}%]"
                    )
                
                # Document avec métadonnées
                doc_with_meta = f"{document}{source_info}{similarity}\n---\n"
                doc_length = len(doc_with_meta)
                
                if total_length + doc_length > max_context_length:
                    break
                
                results.append(doc_with_meta)
                total_length += doc_length
                
        return results
    
    def start_database_tool(self, output_widget):
        """
        Démarre l'outil de création de base de données
        
        Args:
            output_widget: Widget pour afficher les sorties
        """
        # Obtenir le nom de la base de données depuis l'interface
        db_name = self.interface.new_database_name.get().strip()
        
        # Vérifier que le nom est valide
        if not db_name:
            output_widget._textbox.insert("end", "Erreur : Le nom de la base de données ne peut pas être vide.\n", 'system')
            return
        
        # Nettoyer le nom pour éviter les caractères spéciaux
        db_name = self.clean_filename(db_name)
        
        # Vérifier si la base existe déjà
        database_folder = self.config.get('Directories', 'database', fallback='5_database')
        db_path = os.path.join(database_folder, f'{db_name}.pkl')
        index_path = os.path.join(database_folder, f'faiss_index_{db_name}.bin')
        
        if os.path.exists(db_path) or os.path.exists(index_path):
            # Demande de confirmation pour écraser la base existante
            if not messagebox.askyesno("Confirmation", f"La base de données '{db_name}' existe déjà. Voulez-vous l'écraser ?"):
                output_widget._textbox.insert("end", "Création de la base de données annulée.\n", 'system')
                return
        
        # Utiliser la source de données sélectionnée
        source_folder = self.interface.selected_source_folder.get()
        if not source_folder or not os.path.exists(source_folder):
            output_widget._textbox.insert("end", "Erreur : Le dossier source n'existe pas.\n", 'system')
            return
        
        # Récupérer la taille des chunks depuis l'interface
        try:
            chunk_size = int(self.interface.chunk_size_var.get())
            if chunk_size <= 0:
                chunk_size = 500  # Valeur par défaut
        except ValueError:
            chunk_size = 500  # Valeur par défaut
        
        try:
            output_widget._textbox.insert("end", f"Création de la base de données '{db_name}' à partir du dossier '{source_folder}'...\n", 'system')
            self.create_vector_database(db_name, source_folder, chunk_size)
            output_widget._textbox.insert("end", f"Base de données vectorielle '{db_name}' créée avec succès.\n", 'system')
            
            # Mettre à jour la liste des bases disponibles
            self.update_database_list()
            
            # Sélectionner automatiquement la nouvelle base
            self.interface.selected_database.set(db_name)
            
            # Ajout d'un saut de ligne pour séparer ce bloc d'action
            output_widget._textbox.insert("end", "\n", 'system')
        except Exception as e:
            output_widget._textbox.insert("end", f"Erreur lors de la création de la base de données : {e}\n", 'system')
            # Ajout d'un saut de ligne pour séparer ce bloc d'action même en cas d'erreur
            output_widget._textbox.insert("end", "\n", 'system')
    
    def create_vector_database(self, db_name, source_folder='3_transcriptions', chunk_size=500):
        """
        Crée une base de données vectorielle à partir des transcriptions et des PDF.
        Les documents sont divisés en chunks de taille spécifiée.
        
        Args:
            db_name: Nom de la base de données à créer
            source_folder: Dossier contenant les fichiers source
            chunk_size: Taille des chunks de texte
        """
        try:
            # Charger le modèle de transformation
            model_name = 'sentence-transformers/all-MiniLM-L6-v2'
            try:
                model = SentenceTransformer(model_name)
                print(f"Modèle {model_name} chargé avec succès")
            except Exception as e:
                import logging
                logging.getLogger('BlowChatYT').error(f"Erreur lors de l'initialisation du service d'embeddings: {e}")
                raise ValueError(f"Impossible de charger le modèle {model_name}. Veuillez vérifier votre connexion internet et votre token Hugging Face. Erreur: {e}")
            
            # Vérifier que le dossier source existe
            if not os.path.exists(source_folder):
                raise FileNotFoundError(f"Le dossier source '{source_folder}' n'existe pas")
            
            # Lire toutes les transcriptions et les PDF
            documents = []
            filenames = []
            metadata = []
            for filename in os.listdir(source_folder):
                filepath = os.path.join(source_folder, filename)
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
                metadata.extend([{'filename': filename, 'chunk_index': idx, 'source_folder': source_folder} for idx in range(len(text_chunks))])
            
            # Vérifier qu'il y a des documents à traiter
            if not documents:
                raise ValueError(f"Aucun document texte ou PDF trouvé dans le dossier '{source_folder}'")
            
            # Encoder les documents en vecteurs
            vectors = model.encode(documents)
            
            # Dossier de la base de données depuis la configuration
            database_folder = self.config.get('Directories', 'database', fallback='5_database')
            if not os.path.exists(database_folder):
                os.makedirs(database_folder)
            
            # Chemins des fichiers
            index_path = os.path.join(database_folder, f'faiss_index_{db_name}.bin')
            db_path = os.path.join(database_folder, f'{db_name}.pkl')
            
            # Créer l'index FAISS
            dimension = vectors.shape[1]
            index = faiss.IndexFlatL2(dimension)
            index.add(vectors)
            
            # Sauvegarder l'index et les métadonnées
            faiss.write_index(index, index_path)
            with open(db_path, 'wb') as f:
                pickle.dump({
                    'filenames': filenames, 
                    'documents': documents, 
                    'metadata': metadata,
                    'creation_date': os.path.getctime(db_path) if os.path.exists(db_path) else None,
                    'last_modified': os.path.getmtime(db_path) if os.path.exists(db_path) else None,
                    'source_folder': source_folder,
                    'chunk_size': chunk_size,
                    'num_documents': len(documents)
                }, f)
        except Exception as e:
            import logging
            logging.getLogger('BlowChatYT').error(f"Erreur lors de la création de la base de données vectorielle: {e}")
            raise
    
    def enrich_database(self, output_widget):
        """
        Enrichit une base de données vectorielle existante avec de nouveaux documents.
        
        Args:
            output_widget: Widget pour afficher les sorties
        """
        # Obtenir le nom de la base à enrichir
        db_name = self.interface.selected_database.get()
        if not db_name:
            output_widget._textbox.insert("end", "Erreur : Aucune base de données sélectionnée pour l'enrichissement.\n", 'system')
            return
        
        # Obtenir le dossier source
        source_folder = self.interface.selected_source_folder.get()
        if not source_folder or not os.path.exists(source_folder):
            output_widget._textbox.insert("end", "Erreur : Le dossier source n'existe pas ou n'est pas sélectionné.\n", 'system')
            return
        
        # Récupérer la taille des chunks depuis l'interface
        try:
            chunk_size = int(self.interface.chunk_size_var.get())
            if chunk_size <= 0:
                chunk_size = 500  # Valeur par défaut
        except ValueError:
            chunk_size = 500  # Valeur par défaut
        
        try:
            output_widget._textbox.insert("end", f"Enrichissement de la base '{db_name}' avec les documents de '{source_folder}'...\n", 'system')
            self.enrich_vector_database(db_name, source_folder, output_widget, chunk_size)
            # Ajout d'un saut de ligne pour séparer ce bloc d'action
            output_widget._textbox.insert("end", "\n", 'system')
        except Exception as e:
            output_widget._textbox.insert("end", f"Erreur lors de l'enrichissement de la base : {e}\n", 'system')
            # Ajout d'un saut de ligne pour séparer ce bloc d'action même en cas d'erreur
            output_widget._textbox.insert("end", "\n", 'system')
    
    def enrich_vector_database(self, db_name, source_folder, output_widget, chunk_size=500):
        """
        Enrichit une base de données vectorielle existante avec de nouveaux documents.
        
        Args:
            db_name: Nom de la base de données à enrichir
            source_folder: Dossier contenant les nouveaux fichiers
            output_widget: Widget pour afficher les sorties
            chunk_size: Taille des chunks de texte
        """
        try:
            # Vérifier que la base existe
            database_folder = self.config.get('Directories', 'database', fallback='5_database')
            db_path = os.path.join(database_folder, f'{db_name}.pkl')
            index_path = os.path.join(database_folder, f'faiss_index_{db_name}.bin')
            
            if not os.path.exists(db_path) or not os.path.exists(index_path):
                output_widget._textbox.insert("end", f"Erreur : La base de données '{db_name}' n'existe pas.\n", 'system')
                return
            
            # Charger la base existante
            index = faiss.read_index(index_path)
            with open(db_path, 'rb') as f:
                data = pickle.load(f)
            
            # Créer un ensemble des noms de fichiers déjà présents dans la base pour une recherche rapide
            existing_filenames = set()
            if 'filenames' in data:
                existing_filenames = set(data['filenames'])
            
            # Charger le modèle de transformation
            model_name = 'sentence-transformers/all-MiniLM-L6-v2'
            try:
                model = SentenceTransformer(model_name)
                print(f"Modèle {model_name} chargé avec succès pour l'enrichissement")
            except Exception as e:
                import logging
                logging.getLogger('BlowChatYT').error(f"Erreur lors de l'initialisation du service d'embeddings pour l'enrichissement: {e}")
                output_widget._textbox.insert("end", f"Erreur : Impossible de charger le modèle de transformation. Vérifiez votre connexion internet et votre token Hugging Face.\n", 'system')
                return
                
            # Lire les nouveaux documents
            new_documents = []
            new_filenames = []
            new_metadata = []
            skipped_files = []
            
            for filename in os.listdir(source_folder):
                filepath = os.path.join(source_folder, filename)
                
                # Vérifier si le fichier est déjà dans la base (par le nom)
                if filename in existing_filenames:
                    skipped_files.append(filename)
                    continue  # Ignorer les fichiers déjà présents
                    
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
                
                if text_chunks:
                    new_documents.extend(text_chunks)
                    new_filenames.extend([filename] * len(text_chunks))
                    
                    # Index initial pour les nouveaux chunks
                    start_idx = len(data['documents']) if 'documents' in data else 0
                    
                    new_metadata.extend([{
                        'filename': filename, 
                        'chunk_index': start_idx + idx, 
                        'source_folder': source_folder,
                        'added_date': os.path.getmtime(filepath)
                    } for idx in range(len(text_chunks))])
            
            # Afficher les fichiers ignorés
            if skipped_files:
                ignored_msg = f"Les fichiers suivants étaient déjà présents dans la base et ont été ignorés : {', '.join(skipped_files)}"
                output_widget._textbox.insert("end", f"{ignored_msg}\n", 'system')
            
            # Vérifier qu'il y a des documents à ajouter
            if not new_documents:
                output_widget._textbox.insert("end", f"Aucun nouveau document à ajouter depuis '{source_folder}'.\n", 'system')
                # Ajout d'un saut de ligne pour séparer ce bloc d'action
                output_widget._textbox.insert("end", "\n", 'system')
                return
            
            # Encoder les nouveaux documents
            output_widget._textbox.insert("end", f"Encodage de {len(new_documents)} nouveaux segments...\n", 'system')
            new_vectors = model.encode(new_documents)
            
            # Ajouter les nouveaux vecteurs à l'index
            index.add(new_vectors)
            
            # Mettre à jour les métadonnées
            if 'filenames' in data:
                data['filenames'].extend(new_filenames)
            else:
                data['filenames'] = new_filenames
                
            if 'documents' in data:
                data['documents'].extend(new_documents)
            else:
                data['documents'] = new_documents
                
            if 'metadata' in data:
                data['metadata'].extend(new_metadata)
            else:
                data['metadata'] = new_metadata
            
            # Mettre à jour les informations de la base
            data['last_modified'] = os.path.getmtime(db_path) if os.path.exists(db_path) else None
            data['num_documents'] = len(data['documents']) if 'documents' in data else len(new_documents)
            
            # Ajouter les sources
            if 'sources' not in data:
                data['sources'] = []
            
            if source_folder not in data['sources']:
                data['sources'].append(source_folder)
            
            # Sauvegarder l'index et les métadonnées mis à jour
            faiss.write_index(index, index_path)
            with open(db_path, 'wb') as f:
                pickle.dump(data, f)
            
            output_widget._textbox.insert("end", f"Base de données '{db_name}' enrichie avec {len(new_documents)} nouveaux segments.\n", 'system')
            
            # Ajout d'un saut de ligne pour séparer ce bloc d'action
            output_widget._textbox.insert("end", "\n", 'system')
            
            # Si la base actuelle est ouverte, la recharger
            if self.current_database_name == db_name:
                self.load_database(db_name)
        except Exception as e:
            output_widget._textbox.insert("end", f"Erreur lors de l'enrichissement de la base : {e}\n", 'system')
            # Ajout d'un saut de ligne pour séparer ce bloc d'action même en cas d'erreur
            output_widget._textbox.insert("end", "\n", 'system')
    
    def start_youtube_tool(self, channel_name, video_ids_input, num_videos_str, api_key, output_widget):
        """
        Démarre l'outil YouTube pour récupérer les vidéos et transcriptions
        
        Args:
            channel_name: Nom ou ID de la chaîne YouTube
            video_ids_input: Liste d'IDs ou URLs de vidéos séparés par des virgules
            num_videos_str: Nombre de vidéos à récupérer (pour la chaîne)
            api_key: Clé API YouTube
            output_widget: Widget pour afficher les sorties
        """
        if not api_key:
            messagebox.showerror("Erreur", "La clé API YouTube n'est pas définie.")
            return
        
        try:
            num_videos = int(num_videos_str)
        except ValueError:
            num_videos = 5
            self.interface.log_error("Nombre de vidéos invalide, utilisation de la valeur par défaut (5).", output_widget)
        
        if video_ids_input.strip():
            # L'utilisateur a spécifié des vidéos
            video_ids = [vid.strip() for vid in video_ids_input.split(',')]
            videos = self.get_videos_by_ids(video_ids, api_key, output_widget)
        else:
            # Utiliser le nom de la chaîne et le nombre de vidéos
            try:
                videos = self.get_videos_youtube(channel_name, api_key, num_videos, output_widget)
            except Exception as e:
                self.interface.log_error(f"Erreur lors de la récupération des vidéos : {e}", output_widget)
                messagebox.showerror("Erreur", f"Erreur lors de la récupération des vidéos : {e}")
                return
        # Ajout d'un saut de ligne pour séparer les infos générales du traitement des vidéos
        output_widget._textbox.insert("end", "\n", 'system')
        
        # Traitement des vidéos
        for video in videos:
            try:
                video_id = video['id']
                self.interface.log_info(f"Traitement de la vidéo {video_id} : {video['snippet']['title']}", output_widget)
                
                # Récupération de la transcription
                transcription = self.get_transcription(video_id, ['en', 'fr'], output_widget)
                if transcription:
                    # Sauvegarde de la transcription
                    self.save_transcription(video_id, transcription, output_widget)
                    
                    # Génération du rapport markdown
                    self.generate_markdown_report(video, transcription, video.get('statistics', {}), output_widget)
            except Exception as e:
                self.interface.log_error(f"Erreur lors du traitement de la vidéo {video.get('id', 'inconnue')} : {e}", output_widget)
            # Ajout d'un saut de ligne pour séparer chaque bloc de traitement de vidéo
            output_widget._textbox.insert("end", "\n", 'system')
        
        self.interface.log_info("Traitement des vidéos terminé.", output_widget)
        # Ajout d'un séparateur visuel pour bien distinguer chaque traitement
        output_widget._textbox.insert("end", "\n================\n", 'system')
        # Ajout d'un saut de ligne pour séparer ce bloc d'action (traitement d'un lot de vidéos)
        output_widget._textbox.insert("end", "\n", 'system')
        messagebox.showinfo("Succès", "Traitement des vidéos terminé.")
        
        # Mise à jour de la liste des sources après ajout des nouvelles transcriptions
        self.update_source_list()
    
    def get_videos_youtube(self, channel_name, api_key, num_videos, output_widget):
        """
        Récupère les vidéos d'une chaîne YouTube
        
        Args:
            channel_name: Nom ou ID de la chaîne YouTube
            api_key: Clé API YouTube
            num_videos: Nombre de vidéos à récupérer
            output_widget: Widget pour afficher les sorties
            
        Returns:
            list: Liste des vidéos récupérées
        """
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Obtenir l'ID du channel à partir du nom ou de l'ID
        if re.match(r'^UC[a-zA-Z0-9_-]{22}$', channel_name):
            # C'est déjà un ID de chaîne
            channel_id = channel_name
            self.interface.log_info(f"Utilisation de l'ID de chaîne fourni : {channel_id}", output_widget)
        else:
            # Rechercher l'ID à partir du nom
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
            self.interface.log_info(f"ID de chaîne trouvé : {channel_id}", output_widget)
        
        # Obtenir l'ID de la playlist des uploads
        uploads_playlist_id = self.get_channel_uploads_playlist_id(channel_id, api_key)
        self.interface.log_info(f"ID de playlist d'uploads : {uploads_playlist_id}", output_widget)
        
        # Obtenir les vidéos de la playlist des uploads
        playlist_videos = self.get_videos_from_playlist(uploads_playlist_id, api_key, max_videos=num_videos)
        self.interface.log_info(f"Nombre de vidéos trouvées : {len(playlist_videos)}", output_widget)
        
        video_ids = [item['contentDetails']['videoId'] for item in playlist_videos]
        
        # Obtenir les détails et statistiques des vidéos
        videos = []
        for i in range(0, len(video_ids), 50):  # L'API permet max 50 vidéos par requête
            batch_ids = video_ids[i:i+50]
            stats_request = youtube.videos().list(
                part="snippet,statistics",
                id=','.join(batch_ids)
            )
            stats_response = stats_request.execute()
            videos.extend(stats_response['items'])
        
        return videos
    
    def get_channel_uploads_playlist_id(self, channel_id, api_key):
        """
        Récupère l'ID de la playlist des uploads d'une chaîne
        
        Args:
            channel_id: ID de la chaîne YouTube
            api_key: Clé API YouTube
            
        Returns:
            str: ID de la playlist des uploads
        """
        youtube = build('youtube', 'v3', developerKey=api_key)
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        response = request.execute()
        
        if not response['items']:
            raise Exception(f"Chaîne introuvable pour l'ID {channel_id}")
            
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        return uploads_playlist_id
    
    def get_videos_from_playlist(self, playlist_id, api_key, max_videos=None):
        """
        Récupère les vidéos d'une playlist YouTube
        
        Args:
            playlist_id: ID de la playlist YouTube
            api_key: Clé API YouTube
            max_videos: Nombre maximal de vidéos à récupérer
            
        Returns:
            list: Liste des vidéos de la playlist
        """
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
    
    def get_videos_by_ids(self, video_ids, api_key, output_widget):
        """
        Récupère des vidéos à partir de leurs IDs
        
        Args:
            video_ids: Liste d'IDs ou URLs de vidéos YouTube
            api_key: Clé API YouTube
            output_widget: Widget pour afficher les sorties
            
        Returns:
            list: Liste des vidéos récupérées
        """
        youtube = build('youtube', 'v3', developerKey=api_key)
        videos = []
        
        for video_id in video_ids:
            # Extraire l'ID de la vidéo si c'est une URL
            extracted_id = self.extract_video_id(video_id)
            if not extracted_id:
                self.interface.log_error(f"ID de vidéo invalide : {video_id}", output_widget)
                continue
            
            request = youtube.videos().list(
                part="snippet,statistics",
                id=extracted_id
            )
            response = request.execute()
            
            if response['items']:
                video_data = response['items'][0]
                video_data['id'] = extracted_id  # S'assurer que l'ID est correct
                videos.append(video_data)
                self.interface.log_info(f"Vidéo trouvée : {video_data['snippet']['title']}", output_widget)
            else:
                self.interface.log_error(f"Vidéo non trouvée pour l'ID {extracted_id}", output_widget)
        
        return videos
    
    def extract_video_id(self, url):
        """
        Extrait l'ID de la vidéo à partir d'une URL YouTube ou retourne l'ID si déjà donné
        
        Args:
            url: URL YouTube ou ID de vidéo
            
        Returns:
            str: ID de la vidéo ou None si non valide
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
        
        return None
    
    def get_transcription(self, video_id, languages=['en', 'fr'], output_widget=None):
        """
        Récupère la transcription d'une vidéo YouTube via les sous-titres
        
        Args:
            video_id: ID de la vidéo YouTube
            languages: Liste des langues à essayer pour la transcription
            output_widget: Widget pour afficher les sorties
            
        Returns:
            str: Transcription de la vidéo ou None si non disponible
        """
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages)
            transcript = " ".join([item['text'] for item in transcript_list])
            self.interface.log_info(f"Transcription récupérée pour la vidéo {video_id}", output_widget)
            return transcript
        except Exception as e:
            self.interface.log_error(f"Impossible de récupérer la transcription pour la vidéo {video_id}: {e}", output_widget)
            return None
    
    def save_transcription(self, video_id, transcription, output_widget):
        """
        Sauvegarde la transcription dans un fichier texte en UTF-8
        
        Args:
            video_id: ID de la vidéo YouTube
            transcription: Texte de la transcription
            output_widget: Widget pour afficher les sorties
        """
        transcriptions_folder = self.config.get('Directories', 'transcriptions', fallback='3_transcriptions')
        transcription_file = f"{transcriptions_folder}/{video_id}.txt"
        with open(transcription_file, "w", encoding='utf-8') as f:
            f.write(transcription)
        self.interface.log_info(f"Transcription sauvegardée dans {transcription_file}", output_widget)
    
    def generate_markdown_report(self, video, transcription, stats, output_widget):
        """
        Génère un rapport markdown pour une vidéo
        
        Args:
            video: Données de la vidéo
            transcription: Texte de la transcription
            stats: Statistiques de la vidéo
            output_widget: Widget pour afficher les sorties
        """
        video_id = video['id']
        report_content = f"# Rapport de la vidéo : {video['snippet']['title']}\n\n"
        report_content += f"- **Date de publication** : {video['snippet']['publishedAt']}\n"
        report_content += f"- **Description** : {video['snippet']['description']}\n"
        report_content += f"- **Lien** : [https://www.youtube.com/watch?v={video_id}](https://www.youtube.com/watch?v={video_id})\n"
        
        # Ces statistiques peuvent ne pas être disponibles
        if 'viewCount' in stats:
            report_content += f"- **Vues** : {stats['viewCount']}\n"
        
        if 'likeCount' in stats:
            report_content += f"- **Likes** : {stats['likeCount']}\n"
        
        if 'commentCount' in stats:
            report_content += f"- **Commentaires** : {stats['commentCount']}\n"
        
        if 'shareCount' in stats:
            report_content += f"- **Partages** : {stats['shareCount']}\n"
        
        # Ajouter un extrait de la transcription
        if transcription:
            excerpt = transcription[:500] + "..." if len(transcription) > 500 else transcription
            report_content += f"- **Transcription (extrait)** :\n```\n{excerpt}\n```\n"
        else:
            report_content += "- **Transcription** : Non disponible\n"
        
        # Dossier des rapports markdown depuis la configuration
        markdown_folder = self.config.get('Directories', 'markdown_reports', fallback='4_markdown_reports')
        report_file = f"{markdown_folder}/{video_id}_report.md"
        with open(report_file, "w", encoding='utf-8') as f:
            f.write(report_content)
        
        self.interface.log_info(f"Rapport markdown généré : {report_file}", output_widget)
    
    def clean_filename(self, filename):
        """
        Nettoie un nom de fichier en supprimant les caractères non valides
        
        Args:
            filename: Nom de fichier à nettoyer
            
        Returns:
            str: Nom de fichier nettoyé
        """
        filename = filename.strip()
        # Remplacer les caractères non valides par un underscore
        return re.sub(r'[<>:"/\\|?*@]', '', filename).replace(' ', '_')
    
    def get_database_info(self, db_name):
        """
        Récupère les informations d'une base de données
        
        Args:
            db_name: Nom de la base de données
            
        Returns:
            dict: Informations sur la base de données
        """
        database_folder = self.config.get('Directories', 'database', fallback='5_database')
        db_path = os.path.join(database_folder, f'{db_name}.pkl')
        
        if not os.path.exists(db_path):
            return {
                'name': db_name,
                'error': 'Base de données non trouvée'
            }
        
        try:
            with open(db_path, 'rb') as f:
                data = pickle.load(f)
            
            # Récupérer les informations de base
            info = {
                'name': db_name,
                'creation_date': data.get('creation_date'),
                'last_modified': data.get('last_modified'),
                'source_folder': data.get('source_folder', 'Non spécifié'),
                'chunk_size': data.get('chunk_size', 'Non spécifié'),
                'num_documents': data.get('num_documents', len(data.get('documents', []))),
                'num_sources': len(set(data.get('filenames', [])))
            }
            
            return info
        except Exception as e:
            return {
                'name': db_name,
                'error': str(e)
            }
    
    def start(self):
        """Démarre l'application"""
        # Vérifier que la configuration fonctionne correctement avant de démarrer
        self.verify_config_integrity()
        # Démarrer l'interface
        self.interface.start()
        
    def verify_config_integrity(self):
        """Vérifie l'intégrité de la configuration et tente de la réparer si nécessaire"""
        try:
            # Vérifier que toutes les sections requises existent
            required_sections = ['API_KEYS', 'Appearance', 'Assistant', 'Directories', 'Model', 'Stream']
            for section in required_sections:
                if section not in self.config:
                    print(f"Section manquante dans la configuration: {section}")
                    self._create_default_config()
                    return
            
            # Vérifier que les options d'apparence essentielles sont présentes
            appearance_options = ['theme', 'font_size', 'color_system', 'color_user', 
                                'color_model', 'color_model_name', 'color_user_name']
            
            for option in appearance_options:
                if option not in self.config['Appearance']:
                    print(f"Option d'apparence manquante: {option}")
                    # Recréer uniquement les options d'apparence manquantes
                    defaults = {
                        'theme': 'blue',
                        'font_size': '12',
                        'color_system': '#0000FF',
                        'color_user': '#008000',
                        'color_model': '#FF0000',
                        'color_model_name': '#800080',
                        'color_user_name': '#FFA500'
                    }
                    self.config['Appearance'][option] = defaults[option]
            
            # Essayer d'écrire la configuration pour vérifier les permissions d'écriture
            self.save_config()
            
            # Vérifier que le fichier a bien été créé
            if not os.path.exists(self.config_file):
                print("Le fichier de configuration n'a pas été créé malgré la tentative de sauvegarde")
                # Essayer avec un chemin alternatif
                user_dir = os.path.expanduser("~")
                self.config_file = os.path.join(user_dir, "blow_chat_config.ini")
                self.save_config()
                
        except Exception as e:
            print(f"Erreur lors de la vérification de la configuration: {e}")
            # Tenter une réparation d'urgence
            self._create_default_config()
            
    def update_huggingface_token(self, token):
        """
        Met à jour le token Hugging Face et réapplique l'authentification
        
        Args:
            token: Nouveau token Hugging Face à utiliser
        """
        try:
            # Mettre à jour la configuration
            self.update_config('API_KEYS', 'huggingface_token', token)
            
            # Réappliquer l'authentification
            self.init_huggingface_auth()
            
            return True
        except Exception as e:
            print(f"Erreur lors de la mise à jour du token Hugging Face: {e}")
            return False
            

if __name__ == "__main__":
    app = BlowChatApp()
    app.start()