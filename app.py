# -*- coding: utf-8 -*-

"""
	APP_NAME = Tedigo GTalk Client
	APP_VERSION = 0.7
	AUTHOR = Samuel Arroyo
	AUTHOR_EMAIL = samutops@gmail.com
"""

import base64
import sys, os
import sha
from time import sleep, localtime, strftime
import threading
import xmpp
import pygtk
pygtk.require('2.0')
import gtk, gtk.glade, pango

class Application:
	def __init__(self):
		
		# Se carga el constructor y los datos de la interfaz gráfica
		self.builder = gtk.Builder()
		self.builder.add_from_file('app.glade')
		
		# Se cargan los objetos de la interfaz
		self.conectarWindow1 = self.builder.get_object('conectarWindow1')
		self.contactosWindow1 = self.builder.get_object('contactosWindow1')
		self.contactosTreeview1 = self.builder.get_object('contactosTreeview1')
		self.contactosTreeview1.set_headers_visible(False)
		self.conversacion1 = self.builder.get_object('conversacion1')
		self.conversacionBuffer1 = self.conversacion1.get_buffer()
		self.mensaje1 = self.builder.get_object('mensaje1')
		self.enviar1 = self.builder.get_object('enviar1')
		self.avatar1 = self.builder.get_object('avatar1')
		self.username1 = self.builder.get_object('username1')
		self.email1 = self.builder.get_object('email1')
		self.limpiar1 = self.builder.get_object('limpiar1')
		
		# Se inicializa el buffer de texto para las conversaciones
		self.conversacionBuffer1.create_tag('nombre', weight = 700, justification = gtk.JUSTIFY_CENTER)
		self.conversacionBuffer1.create_tag('origen_nombre_fondo', paragraph_background = '#04BFBF')
		self.conversacionBuffer1.create_tag('destino_nombre_fondo', paragraph_background = '#A9C34A')		
		self.conversacionBuffer1.create_tag('cuerpo', indent = 10)
		self.conversacionBuffer1.create_tag('hora', foreground = '#7f7f7f', style = pango.STYLE_ITALIC)
		
		# Se inicializa el menú de selección de estados
		self.estadosCombobox1 = self.builder.get_object('estadosCombobox1')
		self.estadosListstore1 = gtk.ListStore(gtk.gdk.Pixbuf, str)
		self.estadosCombobox1.set_model(self.estadosListstore1)
		self.estadosCellIcono = gtk.CellRendererPixbuf()
		self.estadosCellTexto = gtk.CellRendererText()
		self.estadosCombobox1.pack_start(self.estadosCellIcono, False)
		self.estadosCombobox1.pack_start(self.estadosCellTexto, False)
		self.estadosCombobox1.add_attribute(self.estadosCellIcono, 'pixbuf', 0)
		self.estadosCombobox1.add_attribute(self.estadosCellTexto, 'text', 1)
		
		self.ESTADOS = [['Disponible', 'user-available.svg'],
						['Ocupado', 'user-busy.svg'],
						['Ausente', 'user-away.svg'],
						['Desconectado', 'user-offline.svg']]
		self.ICONS_DIR = './icons/'
		
		for elem in self.ESTADOS:
			row = self.estadosListstore1.append(None)
			self.estadosListstore1.set_value(row, 1, elem[0])
			icon_path = os.path.join(self.ICONS_DIR, elem[1])
			icon = gtk.gdk.pixbuf_new_from_file(icon_path)
			self.estadosListstore1.set_value(row, 0, icon)
		self.estadosCombobox1.set_property('active', 0)
		
		# Se inicializa la vista de los contactos
		self.inicializarListaContactos()		
		
		# Se muestra la ventana Conectar
		self.conectarWindow1.show_all()
		
		# Se conectan las señales al constructor
		self.builder.connect_signals(self)
		
		# Se parametrizan las variables de estado
		self.estado = None
		self.msg = None
		self.disconnect = False

	def inicializarListaContactos(self):
		
		# Se crea un objeto ListStore y se asigna como modelo a la vista
		self.contactosListstore1 = gtk.ListStore(gtk.gdk.Pixbuf, str, str, str, gtk.gdk.Pixbuf, str)
		#                                       (Icono de estado, Estado, Nombre, JID, Foto, Fondo)
		#                                       (      0             1       2     3    4      5  )
		self.contactosTreeview1.set_model(self.contactosListstore1)
		
		# Se crean las columnas
		self.tvEstado = gtk.TreeViewColumn('Estado')
		self.tvNombre = gtk.TreeViewColumn('Nombre')
		self.tvAvatar = gtk.TreeViewColumn('Avatar')
		
		# Se añaden las columnas a la vista
		self.contactosTreeview1.append_column(self.tvEstado)
		self.contactosTreeview1.append_column(self.tvNombre)
		self.contactosTreeview1.append_column(self.tvAvatar)
		
		# Se crean los renders para las celdas
		self.cellEstado = gtk.CellRendererPixbuf()
		self.cellNombre = gtk.CellRendererText()
		self.cellAvatar = gtk.CellRendererPixbuf()
		
		# Se asignan los renders a las columnas
		self.tvEstado.pack_start(self.cellEstado, False)
		self.tvNombre.pack_start(self.cellNombre, False)
		self.tvAvatar.pack_start(self.cellAvatar, False)
		
		# Se indica el tipo de datos que maneja cada render
		self.tvEstado.add_attribute(self.cellEstado, 'pixbuf', 0)
		self.tvNombre.add_attribute(self.cellNombre, 'text', 2)
		self.tvAvatar.add_attribute(self.cellAvatar, 'pixbuf', 4)
		
		self.tvEstado.add_attribute(self.cellEstado, 'cell-background', 5)
		self.tvNombre.add_attribute(self.cellNombre, 'cell-background', 5)
		self.tvAvatar.add_attribute(self.cellAvatar, 'cell-background', 5)
		
		self.contactosListstore1.set_sort_column_id(1, gtk.SORT_ASCENDING)

	def on_estadosCombobox1_changed(self, combobox):
		
		# Se obtiene el elemento seleccionado
		item1 = combobox.get_active()
		self.estadoActual = self.estadosListstore1[item1][1]
		self.estadoCambiado = True
	
	def on_conectarWindow1_delete_event(self, widget, event):
		
		# Se cierra la aplicación
		gtk.main_quit()
	
	def on_connectButton1_clicked(self, widget):
		
		# Se carga el usuario y contraseña introducidos
		user = self.builder.get_object('user1').get_text()
		password = self.builder.get_object('password1').get_text()
		server = 'gmail.com'
		
		# Se rellena la etiqueta de email
		self.email1.set_text(user)
		
		# Se crea un hilo con el cliente que gestiona la conexión
		global client
		client = Client(user, password, server)
		client.start()
		
		self.estadoActual = 'Disponible'
		self.estadoCambiado = False

	def on_limpiar1_clicked(self, widget):
		
		# Se limpia el buffer de conversación
		bounds = self.conversacionBuffer1.get_bounds()
		self.conversacionBuffer1.delete(bounds[0], bounds[1])
		
		# Se indica esto para que se vuelva a mostrar el título del que habla
		client.last_msg = False

	def on_mensaje1_activate(self, widget):
		
		# Se crea un mensaje para que el cliente lo envie
		self.msg = {'to': self.destino, 'body': self.mensaje1.get_text()}
		
		# Se limpia la entrada de texto
		self.mensaje1.set_text('')
	
	def on_contactosWindow1_delete_event(self, widget, event):
		
		self.on_desconectar1_clicked(widget)
		return True

	def on_desconectar1_clicked(self, widget):
		
		# Se indica que se quiere desconectar
		self.disconnect = True
		
		# Se espera a que el cliente se desconecte
		sleep(1)
		
		# Se vacían los datos de ListStore
		self.contactosListstore1.clear()
		
		# Se oculta la ventana Contactos
		self.contactosWindow1.hide_all()
		
		# Se muestra la ventana Conectar
		self.conectarWindow1.show_all()
		
		# Se indica que ya no se quiere desconectar
		self.disconnect = False
		
	def on_contactosTreeview1_row_activated(self, treeview, path, view_column):
		
		# Se obtienen los datos de la celda seleccionada
		iter1 = self.contactosListstore1.get_iter(path)
		self.destino = xmpp.JID(self.contactosListstore1.get_value(iter1, 3)).getStripped()
		self.nombre = self.contactosListstore1.get_value(iter1, 2)
		
		# Se muestra con quién hablamos en el título de la ventana
		self.contactosWindow1.set_title('Hablando con ' + self.nombre)

class Mensaje:
	def __init__(self, origen, destino, cuerpo):
		self.origen = origen
		self.destino = destino
		self.cuerpo = cuerpo
		
		self.SMILEYS = {"+/'\\": 'cowbell.png', "V.v.V": 'crab.gif', "}:-)": 'devil.png', "=(": 'frown.png', 
						"=/": 'slant.png', "=P": 'tongue.png', ":-(": 'frown.png', ":)": 'smile.png',
						">.<": 'wince.png', ":-P": 'tongue.png', ":(:)": 'pig.png', "</3": 'brokenheart.png',
						":-x": 'kiss.png', ":*": 'kiss.png', ":{": 'mustache.png', "<3": 'heart.png',
						":(|)": 'monkey.png', "\\m/": 'rockout.png', ":-o": 'shocked.png', ":D": 'grin.png',
						":(": 'frown.png', "x-(": 'angry.png', "B-)": 'cool.png', ":'(": 'cry.png',
						"=D": 'grin.png', ";)": 'wink.png', ":-|": 'straightface.png', "=)": 'smile.png',
						":-D": 'grin.png', ";^)": 'wink.png', ";-)": 'wink.png', ":-)": 'smile.png',
						":-/": 'slant.png', ":P": 'tongue.png'}
		self.SMILEYS_DIR = './smileys/'						
	
	def mostrarMensaje(self, tags):
		
		conv = app.conversacionBuffer1
		
		if (not client.last_msg) or (self.origen != client.last_msg):
			
			# Si habla otra persona, se muestra el título de quién habla
			startTituloIter = conv.get_end_iter()
			startTituloMark = conv.create_mark('startTituloMark', startTituloIter, True)
		
			conv.insert_with_tags_by_name(startTituloIter, self.origen + '\n', 'nombre')
			
			startTituloIter = conv.get_iter_at_mark(startTituloMark)
			
			conv.apply_tag_by_name(tags[0], startTituloIter, conv.get_end_iter())
		
		# Mostrar el cuerpo del mensaje
		startCuerpoIter = conv.get_end_iter()
		startCuerpoMark = conv.create_mark('startCuerpoMark', startCuerpoIter, True)
		
		self.parsearMensaje(self.cuerpo)
		
		startCuerpoIter = conv.get_iter_at_mark(startCuerpoMark)
		
		conv.apply_tag_by_name('cuerpo', startCuerpoIter, conv.get_end_iter())
		app.conversacion1.scroll_to_mark(conv.get_insert(), 0)
	
	def quicksort(self, list1):
		if list1 == []:
			return []
		else:
			pivot = list1[0]
			lesser = self.quicksort([x for x in list1[1:] if x[0] >= pivot[0]])
			greater = self.quicksort([x for x in list1[1:] if x[0] < pivot[0]])
			return greater + [pivot] + lesser	
	
	def parsearMensaje(self, cuerpo):
		
		conv = app.conversacionBuffer1
		array = []
		
		hora = strftime('%H:%M:%S', localtime())
		horaIter = conv.get_end_iter()
		conv.insert_with_tags_by_name(horaIter, hora + '  ', 'hora')

		for elem in self.SMILEYS:
			result = cuerpo.find(elem)
			while result > -1:
				array.append([result, elem])
				result = cuerpo.find(elem, result + 1)

		array = self.quicksort(array)
		limit = 0
		
		for elem in array:
			conv.insert(conv.get_end_iter(), cuerpo[limit:elem[0]])
			
			icon_path = os.path.join(self.SMILEYS_DIR, self.SMILEYS[elem[1]])
			icon = gtk.gdk.pixbuf_new_from_file(icon_path)
			conv.insert_pixbuf(conv.get_end_iter(), icon)
			
			limit = elem[0] + len(elem[1])

		conv.insert(conv.get_end_iter(), cuerpo[limit:] + '\n')				

class Client(threading.Thread):
	def __init__(self, user, password, server):
		self.user = user
		self.password = password
		self.server = server
		self.contacts = []
		self.PHOTO_DIR = "./photos/"
		self.PHOTO_TYPES = {
		    'image/png': '.png',
		    'image/jpeg': '.jpg',
		    'image/gif': '.gif',
		    'image/bmp': '.bmp',
		    }
		self.last_msg = None
		threading.Thread.__init__(self)

	def messageHandler(self, con, msg):
			if msg.getBody():
				mensaje = Mensaje(str(msg.getFrom().getStripped()), str(msg.getTo()) , str(msg.getBody()))
				mensaje.mostrarMensaje(['destino_nombre_fondo'])
				self.last_msg = str(msg.getFrom().getStripped())
			elif msg.getTag('cha'):
				print msg.getTag('cha')

	def encontrarJID(self, store, jid):
		for row in store:
			if row[3] == jid:
				return True
		return False
	
	def rosterHandler(self, con, stanza):
		for item in stanza.getTag('query').getTags('item'):
			
			cont = app.contactosListstore1
			
			jid, name = item.getAttr('jid'), item.getAttr('name')
			
			if self.encontrarJID(cont, jid):
				return
			
			if not name:
				name = jid
			elif jid == self.jid:
				app.username1.set_text(name)

			iter1 = cont.insert_before(None)
			path = cont.get_path(iter1)
			treerowref = gtk.TreeRowReference(cont, path)
			self.contacts.append([jid, name, treerowref])
			icon_path = os.path.join(app.ICONS_DIR, 'user-offline.svg')
			icon = gtk.gdk.pixbuf_new_from_file(icon_path)
			cont.set(iter1, 0, icon, 1, '3Desconectado', 2, name, 3, jid, 5, '#d0d0d0')		

	def presenceHandler(self, session, pres):
		jid = pres['from'].getStripped()
		
		typ = pres['type']
		if not typ:
			typ = None
		
		# Se obtiene la foto
		photo_path = self.obtainPhoto(jid, session, pres)
		if not photo_path:
			photo_path = None
		
		# Se obtiene el estado del contacto
		show = pres.getTag('show')
		if show:
			show = show.getData()
		else:
			show = None
		
		for contact in self.contacts:
			if contact[0] == jid:
				self.setState(contact[2], show, typ, photo_path)
				break

	def setState(self, myIter, show, typ, photo_path):
		
		cont = app.contactosListstore1
		
		iter1 = cont.get_iter(myIter.get_path())
		
		# Cargar la foto y escalarla a 32px X 32px
		if photo_path:
			avatar = gtk.gdk.pixbuf_new_from_file(photo_path).scale_simple(32, 32, gtk.gdk.INTERP_BILINEAR)	
			cont.set(iter1, 4, avatar)

		if show == 'away':
			icon_path = os.path.join(app.ICONS_DIR, 'user-away.svg')
			icon = gtk.gdk.pixbuf_new_from_file(icon_path)
			cont.set(iter1, 0, icon, 1, '2Ausente', 5, '#fbff8f')
		elif show == 'dnd':
			icon_path = os.path.join(app.ICONS_DIR, 'user-busy.svg')
			icon = gtk.gdk.pixbuf_new_from_file(icon_path)
			cont.set(iter1, 0, icon, 1, '1Ocupado', 5, '#f0a8a8')
		elif typ == 'unavailable':
			icon_path = os.path.join(app.ICONS_DIR, 'user-offline.svg')
			icon = gtk.gdk.pixbuf_new_from_file(icon_path)
			cont.set(iter1, 0, icon, 1, '3Desconectado', 5, '#d0d0d0') 
		else:
			icon_path = os.path.join(app.ICONS_DIR, 'user-available.svg')
			icon = gtk.gdk.pixbuf_new_from_file(icon_path)
			cont.set(iter1, 0, icon, 1, '0Conectado', 5, '#b6f0ae')

	def obtainPhoto(self, jid, session, pres):
		
		vupdate = pres.getTag('x', namespace='vcard-temp:x:update')
		if not vupdate:
			return False
		photo = vupdate.getTag('photo')
		if not photo:
			return False
		photo = photo.getData()
		if not photo:
			return False
		
		# Pedir la foto si no la tenemos
		photo_path = self.get_photo(photo)
		if not photo_path:
			self.request_vcard(session, jid)
		photo_path = self.get_photo(photo)
		if not photo_path:
			return False
		return photo_path

	def append_directory(self, filename):
	    return os.path.join(self.PHOTO_DIR, filename)

	def get_photo(self, photo_hash):
		for ext in self.PHOTO_TYPES.values():
			filepath = self.append_directory(photo_hash + ext)
			if os.path.exists(filepath):
				return filepath
		return False
	
	def request_vcard(self, session, JID):
		n = xmpp.Node('vCard', attrs={'xmlns': xmpp.NS_VCARD})
		iq = xmpp.Protocol('iq', JID, 'get', payload=[n])
		if JID == self.jid:
			return session.SendAndCallForResponse(iq, self.receive_vcard_photo)
		return session.SendAndCallForResponse(iq, self.receive_vcard)
		
	def receive_vcard(self, session, stanza):
		photo = stanza.getTag('vCard').getTag('PHOTO')
		if not photo:
			return False
		photo_type = photo.getTag('TYPE').getData()
		photo_bin = photo.getTag('BINVAL').getData()
		photo_bin = base64.b64decode(photo_bin)
		ext = self.PHOTO_TYPES[photo_type]
		photo_hash = sha.new()
		photo_hash.update(photo_bin)
		photo_hash = photo_hash.hexdigest()
		filename = self.append_directory(photo_hash + ext)
		file(filename, 'wb').write(photo_bin)
		return filename
		
	def receive_vcard_photo(self, session, stanza):
		filename = self.receive_vcard(session, stanza)
		app.avatar1.set_from_file(filename)
		
		# Se oculta la ventana Conectar
		app.conectarWindow1.hide_all()
		
		# Se muestra la ventana Contactos
		app.contactosWindow1.show_all()	

	def run(self):	
		self.jid = xmpp.JID(self.user)
		self.cl = xmpp.Client(self.server)
		
		self.cl.connect()

		self.cl.auth(self.jid.getNode(), self.password)
		self.cl.RegisterHandler('message', self.messageHandler)
		self.cl.RegisterHandler('iq', self.rosterHandler)
		self.cl.RegisterHandler('presence', self.presenceHandler)
		self.cl.sendInitPresence(requestRoster=1)
		
		self.request_vcard(self.cl, self.jid)
		
		while self.cl.Process(1):
			if app.disconnect:
				self.cl.disconnected()
				self.join()
			if app.msg:
				self.cl.send(xmpp.Message(app.msg['to'], app.msg['body'], typ = 'chat'))
				mensaje = Mensaje(self.user, app.msg['to'], app.msg['body'])
				mensaje.mostrarMensaje(['origen_nombre_fondo'])
				self.last_msg = self.user
				app.msg = None
			if app.estadoCambiado:
				if app.estadoActual == app.ESTADOS[0][0]:
					pres = xmpp.Presence(self.jid)
				elif app.estadoActual == app.ESTADOS[1][0]:
					pres = xmpp.Presence(self.jid, show = 'dnd')
				elif app.estadoActual == app.ESTADOS[2][0]:
					pres = xmpp.Presence(self.jid, show = 'away')
				elif app.estadoActual == app.ESTADOS[3][0]:
					pres = xmpp.Presence(self.jid, 'unavailable')	
				self.cl.send(pres)
				app.estadoCambiado = False					
			pass

if __name__ == "__main__":
	try:
		gtk.gdk.threads_init()
		app = Application()
		gtk.threads_enter()
		gtk.main()
		gtk.threads_leave()
	except KeyboardInterrupt:
		pass	
