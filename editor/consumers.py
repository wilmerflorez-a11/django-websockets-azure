import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Documento

# Configurar logger
logger = logging.getLogger(__name__)

class DocumentoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Obtener el ID del documento desde la URL
        self.doc_id = self.scope['url_route']['kwargs']['doc_id']
        self.room_group_name = f'documento_{self.doc_id}'
        
        # Verificar que el usuario esté autenticado
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            logger.warning(f"❌ Intento de conexión sin autenticación al documento {self.doc_id}")
            await self.close()
            return
        
        # Verificar permisos de visualización
        puede_ver = await self.verificar_permisos_visualizacion()
        if not puede_ver:
            logger.warning(f"❌ Usuario {user.username} sin permisos para ver documento {self.doc_id}")
            await self.close()
            return
        
        # Unirse al grupo del documento
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Enviar el contenido actual del documento al conectarse
        contenido = await self.get_documento_contenido()
        await self.send(text_data=json.dumps({
            'tipo': 'inicial',
            'contenido': contenido
        }))
        
        logger.info(f"✅ Usuario {user.username} conectado al documento {self.doc_id}")
    
    async def disconnect(self, close_code):
        # Obtener usuario para el log
        user = self.scope.get('user')
        username = user.username if user and user.is_authenticated else 'Anónimo'
        
        # Salir del grupo
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        logger.info(f"❌ Usuario {username} desconectado del documento {self.doc_id}")
    
    async def receive(self, text_data):
        try:
            user = self.scope.get('user')
            
            # Verificar autenticación
            if not user or not user.is_authenticated:
                logger.warning(f"⚠️ Intento de edición sin autenticación en documento {self.doc_id}")
                return
            
            # Recibir mensaje del WebSocket
            data = json.loads(text_data)
            contenido = data.get('contenido', '')
            
            # Verificar permisos de edición
            puede_editar = await self.verificar_permisos_edicion()
            
            if not puede_editar:
                logger.warning(f"⚠️ Usuario {user.username} sin permisos de edición en documento {self.doc_id}")
                await self.send(text_data=json.dumps({
                    'tipo': 'error',
                    'mensaje': 'No tienes permisos para editar este documento'
                }))
                return
            
            logger.info(f"📝 Usuario {user.username} guardando contenido en documento {self.doc_id}...")
            
            # Guardar en la base de datos
            guardado = await self.save_documento_contenido(contenido)
            
            if guardado:
                logger.info(f"✅ Contenido guardado exitosamente ({len(contenido)} caracteres)")
            else:
                logger.warning(f"⚠️ No se pudo guardar el contenido")
            
            # Enviar el mensaje a todos los miembros del grupo
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'documento_update',
                    'contenido': contenido
                }
            )
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error al decodificar JSON: {e}")
        except Exception as e:
            logger.error(f"❌ Error en receive: {e}", exc_info=True)
    
    async def documento_update(self, event):
        # Recibir mensaje del grupo y enviarlo al WebSocket
        contenido = event['contenido']
        
        await self.send(text_data=json.dumps({
            'tipo': 'update',
            'contenido': contenido
        }))
    
    @database_sync_to_async
    def get_documento_contenido(self):
        try:
            doc = Documento.objects.get(id=self.doc_id)
            logger.info(f"📄 Contenido cargado del documento {self.doc_id}: {len(doc.contenido)} caracteres")
            return doc.contenido
        except Documento.DoesNotExist:
            logger.warning(f"⚠️ Documento {self.doc_id} no existe")
            return ""
        except Exception as e:
            logger.error(f"❌ Error al cargar documento: {e}", exc_info=True)
            return ""
    
    @database_sync_to_async
    def save_documento_contenido(self, contenido):
        try:
            doc = Documento.objects.get(id=self.doc_id)
            doc.contenido = contenido
            doc.save()
            logger.info(f"💾 Documento {self.doc_id} guardado: {len(contenido)} caracteres")
            return True
        except Documento.DoesNotExist:
            logger.warning(f"⚠️ No se puede guardar: Documento {self.doc_id} no existe")
            return False
        except Exception as e:
            logger.error(f"❌ Error al guardar: {e}", exc_info=True)
            return False
    
    @database_sync_to_async
    def verificar_permisos_edicion(self):
        """Verifica si el usuario tiene permisos de edición"""
        try:
            from .models import PermisoDocumento
            user = self.scope.get('user')
            
            if not user or not user.is_authenticated:
                logger.debug(f"   ⚠️ Usuario no autenticado")
                return False
            
            doc = Documento.objects.get(id=self.doc_id)
            
            # El propietario siempre puede editar
            if doc.propietario == user:
                logger.debug(f"   ✅ {user.username} es propietario, puede editar")
                return True
            
            # Verificar permisos compartidos
            tiene_permiso = PermisoDocumento.objects.filter(
                documento=doc,
                usuario=user,
                puede_editar=True
            ).exists()
            
            if tiene_permiso:
                logger.debug(f"   ✅ {user.username} tiene permiso de edición compartido")
            else:
                logger.debug(f"   ⚠️ {user.username} NO tiene permiso de edición")
            
            return tiene_permiso
            
        except Documento.DoesNotExist:
            logger.error(f"   ❌ Documento {self.doc_id} no existe")
            return False
        except Exception as e:
            logger.error(f"   ❌ Error verificando permisos: {e}", exc_info=True)
            return False
    
    @database_sync_to_async
    def verificar_permisos_visualizacion(self):
        """Verifica si el usuario puede ver el documento"""
        try:
            from .models import PermisoDocumento
            user = self.scope.get('user')
            
            if not user or not user.is_authenticated:
                logger.debug(f"   ⚠️ Usuario no autenticado para visualización")
                return False
            
            doc = Documento.objects.get(id=self.doc_id)
            
            # El propietario siempre puede ver
            if doc.propietario == user:
                logger.debug(f"   ✅ {user.username} es propietario, puede ver")
                return True
            
            # Verificar si tiene algún permiso compartido
            tiene_permiso = PermisoDocumento.objects.filter(
                documento=doc,
                usuario=user
            ).exists()
            
            if tiene_permiso:
                logger.debug(f"   ✅ {user.username} tiene permiso de visualización")
            else:
                logger.debug(f"   ⚠️ {user.username} NO tiene permiso de visualización")
            
            return tiene_permiso
            
        except Documento.DoesNotExist:
            logger.error(f"   ❌ Documento {self.doc_id} no existe para verificar visualización")
            return False
        except Exception as e:
            logger.error(f"   ❌ Error verificando permisos de visualización: {e}", exc_info=True)
            return False