"""
Système de stockage cloud pour les logs de tickets
Utilise Google Drive API pour stocker les logs compressés
"""

import os
import json
import zipfile
import io
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
import aiofiles

logger = logging.getLogger(__name__)

class GoogleDriveStorage:
    """Gestionnaire de stockage Google Drive pour les logs de tickets"""
    
    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.json"):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        self.folder_id = None
        self._service = None
        
        # Support des variables d'environnement pour Railway et BisectHosting
        self.use_env_vars = (
            os.getenv('RAILWAY_ENVIRONMENT') is not None or  # Railway
            os.getenv('BISECT_HOSTING') is not None or        # BisectHosting
            os.getenv('GOOGLE_CLIENT_ID') is not None         # Variables présentes
        )
        
    async def initialize(self):
        """Initialise la connexion Google Drive"""
        try:
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            import pickle
            
            creds = None
            
            if self.use_env_vars:
                # Mode Railway - utiliser les variables d'environnement
                creds = await self._load_credentials_from_env()
            else:
                # Mode local - utiliser les fichiers
                # Charger les tokens existants
                if os.path.exists(self.token_file):
                    with open(self.token_file, 'rb') as token:
                        creds = pickle.load(token)
                
                # Si pas de credentials valides, demander l'autorisation
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        if not os.path.exists(self.credentials_file):
                            logger.error(f"Fichier credentials.json manquant: {self.credentials_file}")
                            return False
                        
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, self.scopes)
                        creds = flow.run_local_server(port=0)
                    
                    # Sauvegarder les credentials
                    with open(self.token_file, 'wb') as token:
                        pickle.dump(creds, token)
            
            if not creds:
                logger.error("Impossible d'obtenir les credentials")
                return False
            
            self._service = build('drive', 'v3', credentials=creds)
            
            # Créer ou récupérer le dossier de logs
            await self._ensure_logs_folder()
            
            logger.info("Google Drive initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation Google Drive: {e}")
            return False
    
    async def _load_credentials_from_env(self):
        """Charge les credentials depuis les variables d'environnement (Railway)"""
        try:
            from google.oauth2.credentials import Credentials
            
            # Récupérer les variables d'environnement
            client_id = os.getenv('GOOGLE_CLIENT_ID')
            client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
            refresh_token = os.getenv('GOOGLE_REFRESH_TOKEN')
            
            if not all([client_id, client_secret, refresh_token]):
                logger.error("Variables d'environnement Google manquantes")
                return None
            
            # Créer les credentials
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.scopes
            )
            
            # Rafraîchir le token
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            
            return creds
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des credentials depuis l'environnement: {e}")
            return None
    
    async def _ensure_logs_folder(self):
        """Crée le dossier de logs s'il n'existe pas"""
        try:
            # Chercher le dossier existant
            results = self._service.files().list(
                q="name='MaybeBot Ticket Logs' and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            items = results.get('files', [])
            
            if items:
                self.folder_id = items[0]['id']
                logger.info(f"Dossier de logs trouvé: {self.folder_id}")
            else:
                # Créer le dossier
                file_metadata = {
                    'name': 'MaybeBot Ticket Logs',
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                
                folder = self._service.files().create(
                    body=file_metadata,
                    fields='id'
                ).execute()
                
                self.folder_id = folder.get('id')
                logger.info(f"Dossier de logs créé: {self.folder_id}")
                
        except Exception as e:
            logger.error(f"Erreur lors de la création du dossier: {e}")
    
    async def upload_ticket_logs(self, guild_id: int, ticket_id: int, logs_data: Dict) -> Optional[str]:
        """Upload les logs d'un ticket vers Google Drive"""
        try:
            if not self._service or not self.folder_id:
                logger.error("Google Drive non initialisé")
                return None
            
            # Créer le nom du fichier
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ticket_{guild_id}_{ticket_id}_{timestamp}.zip"
            
            # Compresser les données
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Ajouter les logs JSON
                zip_file.writestr("logs.json", json.dumps(logs_data, ensure_ascii=False, indent=2))
                
                # Ajouter un fichier de métadonnées
                metadata = {
                    "guild_id": guild_id,
                    "ticket_id": ticket_id,
                    "upload_date": datetime.now().isoformat(),
                    "message_count": len(logs_data.get("messages", [])),
                    "event_count": len(logs_data.get("events", [])),
                    "created_at": logs_data.get("created_at"),
                    "status": logs_data.get("status", "closed"),
                    "closed_at": logs_data.get("closed_at")
                }
                
                # Ajouter les informations utilisateur si disponibles
                if logs_data.get("messages"):
                    first_message = logs_data["messages"][0]
                    metadata.update({
                        "user_id": first_message.get("author_id"),
                        "username": first_message.get("author_username"),
                        "discriminator": first_message.get("author_discriminator"),
                        "display_name": first_message.get("author_name"),
                        "avatar_url": first_message.get("author_avatar_url")
                    })
                zip_file.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
            
            zip_buffer.seek(0)
            
            # Upload vers Google Drive
            from googleapiclient.http import MediaIoBaseUpload
            
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            media = MediaIoBaseUpload(
                zip_buffer,
                mimetype='application/zip',
                resumable=True
            )
            
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Logs uploadés avec succès: {filename} (ID: {file_id})")
            
            return file_id
            
        except Exception as e:
            logger.error(f"Erreur lors de l'upload: {e}")
            return None
    
    async def download_ticket_logs(self, file_id: str) -> Optional[Dict]:
        """Télécharge et décompresse les logs d'un ticket"""
        try:
            if not self._service:
                logger.error("Google Drive non initialisé")
                return None
            
            # Télécharger le fichier
            request = self._service.files().get_media(fileId=file_id)
            file_content = request.execute()
            
            # Décompresser
            zip_buffer = io.BytesIO(file_content)
            with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
                # Lire les logs
                logs_json = zip_file.read("logs.json")
                logs_data = json.loads(logs_json.decode('utf-8'))
                
                # Lire les métadonnées
                metadata_json = zip_file.read("metadata.json")
                metadata = json.loads(metadata_json.decode('utf-8'))
                
                logs_data['metadata'] = metadata
            
            return logs_data
            
        except Exception as e:
            if "404" in str(e) or "notFound" in str(e):
                logger.warning(f"Fichier non trouvé sur Google Drive: {file_id}")
            else:
                logger.error(f"Erreur lors du téléchargement: {e}")
            return None
    
    async def list_user_ticket_logs(self, guild_id: int, user_id: int) -> List[Dict]:
        """Liste tous les logs de tickets d'un utilisateur"""
        try:
            if not self._service or not self.folder_id:
                return []
            
            # Chercher les fichiers de logs pour ce serveur
            query = f"'{self.folder_id}' in parents and name contains 'ticket_{guild_id}_' and mimeType='application/zip'"
            
            results = self._service.files().list(
                q=query,
                fields="files(id, name, createdTime, size)",
                orderBy="createdTime desc"
            ).execute()
            
            files = results.get('files', [])
            user_logs = []
            
            for file in files:
                try:
                    # Télécharger et analyser les métadonnées
                    logs_data = await self.download_ticket_logs(file['id'])
                    if logs_data and logs_data.get('metadata'):
                        metadata = logs_data['metadata']
                        
                        # Vérifier si c'est un ticket de cet utilisateur
                        # On peut le faire en vérifiant les messages
                        messages = logs_data.get('messages', [])
                        if messages:
                            first_message = messages[0]
                            if str(first_message.get('author_id')) == str(user_id):
                                # Ajouter les données complètes du ticket
                                ticket_data = {
                                    'file_id': file['id'],
                                    'filename': file['name'],
                                    'created_time': file['createdTime'],
                                    'size': file.get('size', 0),
                                    'metadata': metadata,
                                    'message_count': len(messages),
                                    'event_count': len(logs_data.get('events', [])),
                                    # Ajouter les données principales pour compatibilité
                                    'ticket_id': logs_data.get('ticket_id', 'Inconnu'),
                                    'created_at': logs_data.get('created_at', 'Inconnu'),
                                    'status': logs_data.get('status', 'closed'),
                                    'closed_at': logs_data.get('closed_at'),
                                    'user_id': user_id,
                                    # Ajouter les données utilisateur depuis les métadonnées
                                    'username': metadata.get('username', 'Unknown'),
                                    'discriminator': metadata.get('discriminator', '0000'),
                                    'display_name': metadata.get('display_name', metadata.get('username', 'Unknown')),
                                    'avatar_url': metadata.get('avatar_url'),
                                    'messages': messages,
                                    'events': logs_data.get('events', [])
                                }
                                user_logs.append(ticket_data)
                
                except Exception as e:
                    logger.error(f"Erreur lors de l'analyse du fichier {file['name']}: {e}")
                    continue
            
            return user_logs
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des logs: {e}")
            return []

    async def list_all_ticket_logs(self, guild_id: int) -> List[Dict]:
        """Liste tous les logs de tickets d'un serveur"""
        try:
            if not self._service or not self.folder_id:
                return []
            
            # Chercher les fichiers de logs pour ce serveur
            query = f"'{self.folder_id}' in parents and name contains 'ticket_{guild_id}_' and mimeType='application/zip'"
            
            results = self._service.files().list(
                q=query,
                fields="files(id, name, createdTime, size)",
                orderBy="createdTime desc"
            ).execute()
            
            files = results.get('files', [])
            all_logs = []
            
            for file in files:
                try:
                    # Télécharger et analyser les métadonnées
                    logs_data = await self.download_ticket_logs(file['id'])
                    if logs_data:
                        # Extraire les informations utilisateur des métadonnées ou du premier message
                        messages = logs_data.get('messages', [])
                        metadata = logs_data.get('metadata', {})
                        user_info = {}
                        
                        # Priorité aux métadonnées (plus fiables)
                        if metadata.get('user_id'):
                            user_info = {
                                'user_id': metadata.get('user_id'),
                                'username': metadata.get('username', 'Inconnu'),
                                'discriminator': metadata.get('discriminator', '0000'),
                                'display_name': metadata.get('display_name', 'Inconnu'),
                                'avatar_url': metadata.get('avatar_url')
                            }
                        elif messages:
                            # Fallback sur le premier message
                            first_message = messages[0]
                            user_info = {
                                'user_id': first_message.get('author_id', 'Inconnu'),
                                'username': first_message.get('author_username', first_message.get('author_name', 'Inconnu')),
                                'discriminator': first_message.get('author_discriminator', '0000'),
                                'display_name': first_message.get('author_name', 'Inconnu'),
                                'avatar_url': first_message.get('author_avatar_url')
                            }
                        else:
                            # Fallback sur les données du log
                            user_info = {
                                'user_id': logs_data.get('user_id', 'Inconnu'),
                                'username': logs_data.get('username', 'Inconnu'),
                                'discriminator': logs_data.get('discriminator', '0000'),
                                'display_name': logs_data.get('username', 'Inconnu'),
                                'avatar_url': logs_data.get('avatar_url')
                            }
                        
                        # Ajouter les données complètes du ticket
                        ticket_data = {
                            'file_id': file['id'],
                            'filename': file['name'],
                            'created_time': file['createdTime'],
                            'size': file.get('size', 0),
                            'message_count': len(messages),
                            'event_count': len(logs_data.get('events', [])),
                            # Ajouter les données principales pour compatibilité
                            'ticket_id': logs_data.get('ticket_id', 'Inconnu'),
                            'user_id': user_info['user_id'],
                            'username': user_info['username'],
                            'discriminator': user_info['discriminator'],
                            'display_name': user_info.get('display_name', user_info['username']),
                            'avatar_url': user_info['avatar_url'],
                            'created_at': logs_data.get('created_at', 'Inconnu'),
                            'status': logs_data.get('status', 'closed'),
                            'closed_at': logs_data.get('closed_at'),
                            'messages': messages,
                            'events': logs_data.get('events', [])
                        }
                        all_logs.append(ticket_data)
                
                except Exception as e:
                    logger.error(f"Erreur lors de l'analyse du fichier {file['name']}: {e}")
                    continue
            
            logger.info(f"Récupéré {len(all_logs)} logs de tickets pour le serveur {guild_id}")
            return all_logs
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des logs du serveur: {e}")
            return []
    
    async def cleanup_old_logs(self, days: int = 30):
        """Nettoie les anciens logs (plus de X jours)"""
        try:
            if not self._service or not self.folder_id:
                return
            
            cutoff_date = datetime.now().timestamp() - (days * 24 * 60 * 60)
            cutoff_iso = datetime.fromtimestamp(cutoff_date).isoformat()
            
            # Chercher les anciens fichiers
            query = f"'{self.folder_id}' in parents and createdTime < '{cutoff_iso}' and mimeType='application/zip'"
            
            results = self._service.files().list(
                q=query,
                fields="files(id, name, createdTime)"
            ).execute()
            
            files = results.get('files', [])
            
            for file in files:
                try:
                    self._service.files().delete(fileId=file['id']).execute()
                    logger.info(f"Ancien log supprimé: {file['name']}")
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression de {file['name']}: {e}")
            
            logger.info(f"Nettoyage terminé: {len(files)} fichiers supprimés")
            
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")

class CloudTicketLogger:
    """Gestionnaire de logs de tickets avec stockage cloud"""
    
    def __init__(self, bot, cloud_storage: GoogleDriveStorage):
        self.bot = bot
        self.cloud_storage = cloud_storage
        self.ticket_cache = {}  # Cache temporaire des messages par ticket
        self.max_cache_size = 1000  # Limite du cache
    
    async def initialize(self):
        """Initialise le système de logs cloud"""
        return await self.cloud_storage.initialize()
    
    async def log_message(self, message):
        """Enregistre un message dans le cache temporaire"""
        if not message.guild or not message.channel:
            return
        
        # Vérifier si c'est un canal de ticket
        ticket_data = await self.bot.db.query(
            "SELECT * FROM active_tickets WHERE channel_id = %s AND guild_id = %s",
            (str(message.channel.id), str(message.guild.id)),
            fetchone=True
        )
        
        if not ticket_data:
            return
        
        ticket_key = f"{message.guild.id}_{message.channel.id}"
        
        # Initialiser le cache pour ce ticket
        if ticket_key not in self.ticket_cache:
            self.ticket_cache[ticket_key] = {
                "ticket_id": str(message.channel.id),
                "guild_id": str(message.guild.id),
                "created_at": message.channel.created_at.isoformat(),
                "messages": [],
                "events": []
            }
        
        # Ajouter le message au cache
        message_entry = {
            "message_id": str(message.id),
            "author_id": str(message.author.id),
            "author_name": message.author.display_name,  # Nom d'affichage (nickname ou nom Discord)
            "author_username": message.author.name,  # Vrai nom Discord
            "author_discriminator": message.author.discriminator,  # Discriminateur Discord
            "author_avatar_url": str(message.author.avatar.url) if message.author.avatar else None,
            "content": message.content,
            "timestamp": message.created_at.isoformat(),
            "attachments": [
                {
                    "filename": att.filename,
                    "url": att.url,
                    "size": att.size
                } for att in message.attachments
            ],
            "embeds": [
                {
                    "title": embed.title,
                    "description": embed.description,
                    "color": embed.color.value if embed.color else None,
                    "fields": [
                        {
                            "name": field.name,
                            "value": field.value,
                            "inline": field.inline
                        } for field in embed.fields
                    ]
                } for embed in message.embeds
            ]
        }
        
        self.ticket_cache[ticket_key]["messages"].append(message_entry)
        
        # Limiter la taille du cache
        if len(self.ticket_cache) > self.max_cache_size:
            oldest_keys = list(self.ticket_cache.keys())[:100]
            for key in oldest_keys:
                del self.ticket_cache[key]
    
    async def log_ticket_event(self, guild_id: int, channel_id: int, event_type: str, 
                              user_id: int, user_name: str, details: str = ""):
        """Enregistre un événement de ticket dans le cache"""
        ticket_key = f"{guild_id}_{channel_id}"
        
        if ticket_key not in self.ticket_cache:
            self.ticket_cache[ticket_key] = {
                "ticket_id": str(channel_id),
                "guild_id": str(guild_id),
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "events": []
            }
        
        event_entry = {
            "type": event_type,
            "user_id": str(user_id),
            "user_name": user_name,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        
        self.ticket_cache[ticket_key]["events"].append(event_entry)
    
    async def finalize_ticket_logs(self, guild_id: int, channel_id: int) -> Optional[str]:
        """Finalise les logs d'un ticket et les upload vers le cloud"""
        ticket_key = f"{guild_id}_{channel_id}"
        
        if ticket_key not in self.ticket_cache:
            logger.warning(f"Aucun log trouvé pour le ticket {channel_id}")
            return None
        
        try:
            # Récupérer les logs du cache
            logs_data = self.ticket_cache[ticket_key]
            
            # Upload vers Google Drive
            file_id = await self.cloud_storage.upload_ticket_logs(
                guild_id, channel_id, logs_data
            )
            
            # Supprimer du cache
            del self.ticket_cache[ticket_key]
            
            return file_id
            
        except Exception as e:
            logger.error(f"Erreur lors de la finalisation des logs: {e}")
            return None
    
    async def get_user_ticket_logs(self, guild_id: int, user_id: int) -> List[Dict]:
        """Récupère tous les logs de tickets d'un utilisateur depuis le cloud"""
        return await self.cloud_storage.list_user_ticket_logs(guild_id, user_id)
    
    async def get_ticket_logs(self, file_id: str) -> Optional[Dict]:
        """Récupère les logs d'un ticket spécifique depuis le cloud"""
        return await self.cloud_storage.download_ticket_logs(file_id)
