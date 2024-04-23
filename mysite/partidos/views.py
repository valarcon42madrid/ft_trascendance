# coding=utf-8

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
#from django.contrib.auth import authenticate, login, logout 
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponse, JsonResponse
#from django.template.loader import get_template
from django.template import Context, Template
from django.utils.translation import gettext_lazy as _
from django.utils.translation import activate
from django.db.models import Q, F
from django.db import IntegrityError
from .models import Partido_enJuego, Partido_historia
from torneos.views import torneo_jugar, torneo_result
from torneos.models import Torneo, FaseTorneo
from general.views import activate_language
from general.models import UserSettings
from web3 import Web3
from web3.contract import Contract
from web3.auto import w3
from eth_account import Account
import re
import os
import datetime
import math

# constantes globales

patata = 1

campo = { "ancho": 800, "alto": 400 }
sep = 15 # separacion del jugador con el fondo de la pista
raqueta = { "ancho": 10, "alto": 90 }
pelota = { "ancho": 15, "alto": 15 }

jugador1_x = 0 - campo["ancho"] / 2 + sep # 0 = centro
jugador2_x = 0 + campo["ancho"] / 2 - sep # 0 = centro

min_y = - campo["alto"] / 2
max_y = campo["alto"] / 2
min_x = - campo["ancho"] / 2
max_x = campo["ancho"] / 2

dist_x = (raqueta["ancho"] + pelota["ancho"]) / 2 # distancia x para choque de raqueta y pelota
dist_y = (raqueta["alto"] + pelota["alto"]) / 2 # distancia y para choque de raqueta y pelota

jugador1_rebote_raqueta = jugador1_x + raqueta["ancho"] / 2
jugador2_rebote_raqueta = jugador2_x - raqueta["ancho"] / 2

max_puntuacion = 3

jugador_velocidad = 140
pelota_velocidad_c = 300
pelota_velocidad_m = pelota_velocidad_c * math.sqrt(2) 

def agregar_o_actualizar_usuario(login, score, tournamentId):

	contract_abi = [
	{
		"anonymous": False,
		"inputs": [
			{
				"indexed": False,
				"internalType": "string",
				"name": "_login",
				"type": "string"
			},
			{
				"indexed": False,
				"internalType": "uint8",
				"name": "_score",
				"type": "uint8"
			},
			{
				"indexed": False,
				"internalType": "uint32",
				"name": "_tournamentId",
				"type": "uint32"
			}
		],
		"name": "userScore",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "_login",
				"type": "string"
			},
			{
				"internalType": "uint8",
				"name": "_score",
				"type": "uint8"
			},
			{
				"internalType": "uint32",
				"name": "_tournamentId",
				"type": "uint32"
			}
		],
		"name": "doUser",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "",
				"type": "string"
			}
		],
		"name": "Users",
		"outputs": [
			{
				"internalType": "string",
				"name": "login",
				"type": "string"
			},
			{
				"internalType": "uint8",
				"name": "score",
				"type": "uint8"
			},
			{
				"internalType": "uint32",
				"name": "tournamentId",
				"type": "uint32"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]

	contract_address = os.environ.get("COADDR")
	
	w3 = Web3(Web3.HTTPProvider('https://rpc2.sepolia.org'))

	private_key = os.environ.get("PRKEY")

	cuenta = w3.eth.account.from_key(private_key).address

	w3.eth.default_account = w3.eth.account.from_key(private_key).address

	contract = w3.eth.contract(address=contract_address, abi=contract_abi)

	nonce = w3.eth.get_transaction_count(w3.eth.default_account)

	txn_dict = contract.functions.doUser(login, score, tournamentId).build_transaction({
	 	'from': cuenta,
        'value': 0,
        'gas': 1000000,
        'gasPrice': w3.to_wei('50', 'gwei'),  # Reemplaza '50' con el precio de gas deseado en gwei
        'nonce': nonce,
    })

	signed_txn = w3.eth.account.sign_transaction(txn_dict, private_key=private_key)
	tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
	# Esta ultima no es necesaria, pero la consideran una buena práctica (pero no la he probado aun)
	#w3.eth.waitForTransactionReceipt(tx_hash)

def BlockPartido(partido):
	if partido.terminado == False and partido.tipo == "T":
		if partido.jugador1_marcador >= partido.jugador2_marcador:
			# print("JUGADOR fuera!\n\n")
			# print(partido.jugador2.username)
			# print(partido.nFaseTorneo)
			# print(partido.idTorneo)
			agregar_o_actualizar_usuario(partido.jugador2.username, partido.nFaseTorneo - 1, partido.idTorneo)
		else:
			# print("JUGADOR fuera!\n\n")
			# print(partido.jugador1.username)
			# print(partido.nFaseTorneo)
			# print(partido.idTorneo)
			agregar_o_actualizar_usuario(partido.jugador1.username, partido.nFaseTorneo - 1, partido.idTorneo)
def ajusta_velocidad_pelota(vx, vy):
	v_m = math.sqrt(vx*vx + vy*vy)
	if v_m != pelota_velocidad_m:
		mul = pelota_velocidad_m / v_m
		vx2 = vx * mul
		vy2 = vy * mul
		if abs(vx2) < (pelota_velocidad_c / 2):
			vx2 = fSigno(vx2) * pelota_velocidad_c / 2
		result = { 'x': vx2, 'y': vy2, }
	else:
		result = { 'x': vx, 'y': vy, }
	if result['x'] < 0:
		result['x'] = result['x'] * -1
	return result

def ajusta_velocidad_pelota2(vx, vy):
	v_m = math.sqrt(vx*vx + vy*vy)
	if v_m != pelota_velocidad_m:
		mul = pelota_velocidad_m / v_m
		vx2 = vx * mul
		vy2 = vy * mul
		if abs(vx2) < (pelota_velocidad_c / 2):
			vx2 = fSigno(vx2) * pelota_velocidad_c / 2
		result = { 'x': vx2, 'y': vy2, }
	else:
		result = { 'x': vx, 'y': vy, }
	if result['x'] > 0:
		result['x'] = result['x'] * -1
	return result

def fSigno(d):
	if d>0:
		return 1
	else:
		return -1

def fLimit(val, min, max):
	r = val
	if val < min:
		r = min
	if val > max:
		r = max
	return r

def diffTimeSec(t1, t2):
	s = t2.timestamp() - t1.timestamp()
	#s = dt.seconds
	#ms = dt.microseconds
	#ss = s + ms / 1e6
	return s

# Para el jugador 1 del partido: actualiza la posicion, cambia el update
def fMoverJugador1(partido):
	t1 = partido.jugador1_actualizacion
	t2 = datetime.datetime.now()
	s = diffTimeSec(t1, t2)
	new_y = partido.jugador1_y + partido.jugador1_velocidad_y * s
	new_y = fLimit(new_y, min_y, max_y)
	partido.jugador1_y = new_y
	partido.jugador1_actualizacion = t2

# Para el jugador 1 del partido: anota la nueva velocidad segun la tecla
def fKeyJugador1(partido, key):
	if key == "up_end" or key == "down_end":
		partido.jugador1_velocidad_y = 0
	elif key == "down_begin":
		partido.jugador1_velocidad_y = jugador_velocidad
	elif key == "up_begin":
		partido.jugador1_velocidad_y = - jugador_velocidad
		
# Para el jugador 2 del partido: actualiza la posición, cambia el update
def fMoverJugador2(partido):
	t1 = partido.jugador2_actualizacion
	t2 = datetime.datetime.now()
	s = diffTimeSec(t1, t2)
	new_y = partido.jugador2_y + partido.jugador2_velocidad_y * s
	new_y = fLimit(new_y, min_y, max_y)
	partido.jugador2_y = new_y
	partido.jugador2_actualizacion = t2

# Para el jugador 2 del partido: anota la nueva velocidad según la tecla
def fKeyJugador2(partido, key):
	if key=="up_end" or key == "down_end":
		partido.jugador2_velocidad_y = 0
	elif key == "down_begin":
		partido.jugador2_velocidad_y = jugador_velocidad
	elif key == "up_begin":
		partido.jugador2_velocidad_y = - jugador_velocidad

# mensaje Key = idPartido + ";" + numJugador + ";" + key
# key: down_begin, down_end, up_begin, up_end
def fRecibirKey(mensajeKey):
	aMensajeKey = mensajeKey.split(";")
	idPartido = int(aMensajeKey[0])
	numJugador = int(aMensajeKey[1]) # 0 o 1
	key = aMensajeKey[2]
	try:
		partido = Partido_enJuego.objects.get(id=idPartido)
	except Partido_enJuego.DoesNotExist:
		return
	if key == "stop":
		partido.desconectado = True
		partido.terminado = True
		partido.save()
	elif numJugador == 1:
		fMoverJugador1(partido)
		fKeyJugador1(partido, key)
	elif numJugador == 2:
		fMoverJugador2(partido)	
		fKeyJugador2(partido, key)		
	partido.save() # modifica el partido

def fJugador1TocaPelota(partido):
	if abs(partido.pelota_x - jugador1_x) > dist_x:
		return False
	if abs(partido.pelota_y - partido.jugador1_y) > dist_y:
		return False
	if partido.pelota_x < jugador1_x:
		return False
	return True

def fJugador2TocaPelota(partido):
	if abs(partido.pelota_x - jugador2_x) > dist_x:
		return False
	if abs(partido.pelota_y - partido.jugador2_y) > dist_y:
		return False
	if partido.pelota_x > jugador2_x:
		return False
	return True

def fPartidoAnotarResultado(partido):
	# partido = Partido_enJuego
	if partido.tipo == "R": # partido rápido
		partido2 = Partido_historia() # nuevo
		partido2.partido_enJuego_id = partido.id 
		# partido_enJuego_id es unique para que las conexiones de los dos jugadores no cree dos registros
		partido2.jugador1 = partido.jugador1
		partido2.jugador2 = partido.jugador2
		partido2.jugador1_marcador = partido.jugador1_marcador
		partido2.jugador2_marcador = partido.jugador2_marcador
		partido2.comienzo = partido.comienzo
		partido2.fin = partido.fin 
		try:
			partido2.save()
		except IntegrityError:
			# partido_enJuego_id es unique para que las conexiones de los dos jugadores no cree dos registros
			# el partido2 (Partido_historia) ya se ha creado
			return
		return
	elif partido.tipo == "T": # Torneo
		# no pasa nada si se hace esto dos veces, una por la conexión de cada uno de los dos jugadores
		torneo_result(
			partido.idTorneo, partido.nFaseTorneo, 
			partido.jugador1.id, partido.jugador2.id, 
			partido.jugador1_marcador, partido.jugador2_marcador
		)
	
def fMoverPelota(partido):
	t2 = datetime.datetime.now()
	global patata
	if partido.tipo == "T" and partido.limiteTiempoTorneo < t2:
		if patata != 0:
			patata = 0
			BlockPartido(partido)
		partido.terminado = True
		partido.fin = t2
		fPartidoAnotarResultado(partido)
		patata = 1
		return
	if partido.tipo == "T" and (partido.estadoTorneo == "1" or partido.estadoTorneo == "2") and partido.limiteTiempoConUnJugador < t2:
		if patata != 0:
			patata = 0
			BlockPartido(partido)
		partido.terminado = True
		partido.fin = t2
		if partido.estadoTorneo == "1":
			partido.jugador2_marcador = -1 # -1 indica "no presentado"
		else:
			partido.jugador1_marcador = -1 # -1 indica "no presentado"
		fPartidoAnotarResultado(partido)
		patata = 1
		return		
	if partido.pausa: # estaba en pausa y la pausa ha acabado
		s = diffTimeSec(partido.finDePausa, t2)
		if s > 0: # estaba en pausa y la pausa ha acabado
			partido.pausa = False
			partido.pelota_x = 0
			partido.pelota_y = 0
			partido.pelota_actualizacion = t2 # en todos los casos se fija pelota_actualizacion
			return
	if partido.pausa:
		partido.pelota_actualizacion = t2 # en todos los casos se fija pelota_actualizacion
		return
	t1 = partido.pelota_actualizacion
	s = diffTimeSec(t1, t2)
	# y
	new_y = partido.pelota_y + partido.pelota_velocidad_y * s
	if new_y > max_y: # rebote en pared
		new_y = max_y - (new_y - max_y)
		partido.pelota_velocidad_y = -partido.pelota_velocidad_y # cambio de dirección
	elif new_y < min_y: #rebote en pared
		new_y = min_y + (min_y - new_y)
		partido.pelota_velocidad_y = -partido.pelota_velocidad_y # cambio de dirección
	partido.pelota_y = new_y
	# x
	new_x = partido.pelota_x + partido.pelota_velocidad_x * s	
	if new_x > max_x:	# consigue punto jugador 1
		s1 = datetime.timedelta(seconds=1)
		partido.pausa = True
		partido.finDePausa = t2 + s1
		partido.jugador1_marcador = partido.jugador1_marcador + 1
		partido.pelota_x = 0 # la pelota vuelve al centro pero conserva su velociad
		partido.pelota_y = 0
		partido.pelota_velocidad_x = fSigno(partido.pelota_velocidad_x) * pelota_velocidad_c
		partido.pelota_velocidad_y = fSigno(partido.pelota_velocidad_y) * pelota_velocidad_c
		if partido.jugador1_marcador >= max_puntuacion:
			if patata != 0:
				patata = 0
				BlockPartido(partido)
			partido.terminado = True
			partido.fin = t2
			fPartidoAnotarResultado(partido)
			patata = 1
		partido.pelota_actualizacion = t2 # en todos los casos se fija pelota_actualizacion
		return
	elif new_x < min_x:	# consigue punto jugador 2
		s1 = datetime.timedelta(seconds=1)
		partido.pausa = True
		partido.finDePausa = t2 + s1
		partido.jugador2_marcador = partido.jugador2_marcador + 1
		partido.pelota_x = 0 # la pelota vuelve al centro pero conserva su velociad
		partido.pelota_y = 0
		partido.pelota_velocidad_x = fSigno(partido.pelota_velocidad_x) * pelota_velocidad_c
		partido.pelota_velocidad_y = fSigno(partido.pelota_velocidad_y) * pelota_velocidad_c
		if partido.jugador2_marcador >= max_puntuacion:
			if patata != 0:
				patata = 0
				BlockPartido(partido)
			partido.terminado = True
			partido.fin = t2
			fPartidoAnotarResultado(partido)
			patata = 1
		partido.pelota_actualizacion = t2 # en todos los casos se fija pelota_actualizacion
		return
	partido.pelota_x = new_x # actualiza de momento
	if fJugador1TocaPelota(partido):
		if new_x < jugador1_rebote_raqueta:
			new_x = jugador1_rebote_raqueta + (jugador1_rebote_raqueta - new_x)
		suma_vy = math.sin((partido.pelota_y - partido.jugador1_y) / dist_y) * pelota_velocidad_c * 0.8
		partido.pelota_velocidad_y += suma_vy
		partido.pelota_velocidad_x = - partido.pelota_velocidad_x # rebote en raqueta
		result = ajusta_velocidad_pelota(partido.pelota_velocidad_x, partido.pelota_velocidad_y)
		partido.pelota_velocidad_x = result['x']
		partido.pelota_velocidad_y = result['y']
	if fJugador2TocaPelota(partido):
		if new_x > jugador2_rebote_raqueta:
			new_x = jugador2_rebote_raqueta - (new_x - jugador2_rebote_raqueta)
		suma_vy = math.sin((partido.pelota_y - partido.jugador2_y) / dist_y) * pelota_velocidad_c * 0.8
		partido.pelota_velocidad_y += suma_vy
		partido.pelota_velocidad_x = - partido.pelota_velocidad_x # rebote en raqueta
		result = ajusta_velocidad_pelota2(partido.pelota_velocidad_x, partido.pelota_velocidad_y)
		partido.pelota_velocidad_x = result['x']
		partido.pelota_velocidad_y = result['y']
	partido.pelota_x = new_x
	partido.pelota_actualizacion = t2 # en todos los casos se fija pelota_actualizacion

# mensajeStatus = idPartido;myLanguage
def fEnviarStatus(mensajeStatus):
	aMensajeStatus = mensajeStatus.split(";")
	idPartido = int(aMensajeStatus[0])
	myLanguage = aMensajeStatus[1]
	try:
		partido = Partido_enJuego.objects.get(id=idPartido) 
	except Partido_enJuego.DoesNotExist:
		return
	fMoverPelota(partido) # cambia pelota_actualizacion
	fMoverJugador1(partido)
	fMoverJugador2(partido)
	partido.save()
	activate(myLanguage)
	status = "pcxy," + str(int(partido.pelota_x)) + "," + str(int(partido.pelota_y)) + ";"
	status = status + "j1cy," + str(int(partido.jugador1_y)) + ";"
	status = status + "j2cy," + str(int(partido.jugador2_y)) + ";"
	if partido.pausa:
		status = status + "j1m," + str(partido.jugador1_marcador) + ";"
		status = status + "j2m," + str(partido.jugador2_marcador) + ";"
	if not partido.empezado:
		status =	status + "e," +	_("Waiting player 2") + ";"
		if partido.tipo == "T":
			user_settings, created = UserSettings.objects.get_or_create(user=partido.jugador1)
			alias1 = user_settings.alias
			if alias1 == "":
				alias1 = partido.jugador1.username
			user_settings, created = UserSettings.objects.get_or_create(user=partido.jugador2)
			alias2 = user_settings.alias
			if alias2 == "":
				alias2 = partido.jugador2.username
			status = status + "j1n," + alias1 + ";"
			status = status + "j2n," + alias2 + ";"
		else: # "R"
			status = status + "j1n," + partido.jugador1.username + ";"
	else:
		t2 = datetime.datetime.now()
		t1 = partido.comienzo
		if not (partido.rearranque is None):
			t1 = partido.rearranque
		s = diffTimeSec(t1, t2)
		if s<2:
			# los nombre sirven especialmente para la vista del jugador que acaba de entrar
			if partido.tipo == "T":
				user_settings, created = UserSettings.objects.get_or_create(user=partido.jugador1)
				alias1 = user_settings.alias
				if alias1 == "":
					alias1 = partido.jugador1.username
				user_settings, created = UserSettings.objects.get_or_create(user=partido.jugador2)
				alias2 = user_settings.alias
				if alias2 == "":
					alias2 = partido.jugador2.username
				status = status + "j1n," + alias1 + ";"
				status = status + "j2n," + alias2 + ";"
			else:
				status =	status + "j1n," + partido.jugador1.username + ";"
				status =	status + "j2n," + partido.jugador2.username + ";"
			status = status + "e," + _("Playing") + ";"
	if partido.terminado:
		status =	status + "j1m," + str(partido.jugador1_marcador) + ";"
		status =	status + "j2m," + str(partido.jugador2_marcador) + ";"
		status = status + "e," + _("Match over") + ";"
		status = status + "stop;"
	return status

def fun_keys(request): # process aj_keys
	if not request.user.is_authenticated:
		return
	mensajeKey = request.POST.get('mensaje') # mensajeKey = idPartido + ";" + numJugador + ";" + key # numJugador 1 o 2 (izq o der)
	fRecibirKey(mensajeKey)
	return JsonResponse({}, status=200)

def fun_status(request): # process aj_status
	if not request.user.is_authenticated:
		return
	mensajeStatus = request.POST.get('mensaje') # mensajeStatus = idPartido;myLanguage
	strStatus = fEnviarStatus(mensajeStatus)
	return JsonResponse({"mensaje": strStatus}, status=200)
	
def fun_rearranque(request, vTipo): # vTipo: "T" = torneo, "R" = rápida
	result = { 'ok': False, 'response': None, }
	if not request.user.is_authenticated:
		return result
	currentUser = request.user
	while True:
		partidos = Partido_enJuego.objects.filter(
			Q(tipo=vTipo) & ( Q(jugador1=currentUser) | Q(jugador2=currentUser) ) & Q(terminado=False)  & Q(desconectado=False)
		)
		if partidos:
			partido = partidos[0]
		else:
			return result
		t2 = datetime.datetime.now()
		t1 = partido.pelota_actualizacion
		s = diffTimeSec(t1, t2)
		if (s > 2) or (partido.jugador1 == partido.jugador2): # si no se actualiza la pelota debe ser por desconexion
			partido.desconectado = True
			partido.save()
		else:
			partido.rearranque = t2
			partido.save()
			break # encontrado partido a continuar
	myLanguage = request.session.get('myLanguage')
	if myLanguage is None:
		myLanguage = request.LANGUAGE_CODE
	if currentUser == partido.jugador1:
		numJugador = 1 # 1: izq, 2: der
	else:
		numJugador = 2
	idPartido = partido.id
	limiteTiempoTorneo = ''
	if vTipo == "T":
		limiteTiempoTorneo = partido.limiteTiempoTorneo
	mycontext = {
		'idPartido': idPartido,
		'numJugador': numJugador, # 1: izq, 2: der
		'myLanguage': myLanguage,
		'limiteHoraPartido': limiteTiempoTorneo,
	}
	# numJugador: 1 = izq, 2 = der
	result['response'] = render(request, 'partidos/pantallaPong_t.html', mycontext)
	# enviar el html-javascript que atiende el partido cambiando: idPartido, numJugador, myLanguage, limiteHoraPartido
	if partido.empezado == True or (partido.desconectado == False and partido.tipo == "R"):
		result['ok'] = True
	return result

def numero_fases(idTorneo):
	instancia = Torneo.objects.get(id=idTorneo)
	x = instancia.jugadores.count()
	fases = 0
	while x > 1:
		fases = fases + 1
		x = x / 2
	return fases

def player_has_played(usern, idTorneo, fase):
	instancia = Torneo.objects.get(id=idTorneo)
	try:
		faseTorneo = FaseTorneo.objects.get(torneo=instancia, fase=fase)
	except FaseTorneo.DoesNotExist:
		return False
	lpr = faseTorneo.lista_partidos_resultados
	name = usern + " {"
	if name in lpr:
		return False
	# jugador1_marcador
	return True


def fun_arranque_torneo(request): #arranque torneo
	if not request.user.is_authenticated:
		return redirect('home')
	
	# << nuevo
	currentUser = request.user
	dd = torneo_jugar(currentUser.id)
	# dd  = { 'ok': True, 'idTorneo': idTorneo, 'fase': fase, 'idJugador1': idJugador1, 'idJugador2': idJugador2 }
	if not dd['ok'] :
		return redirect('home_section')
	IDE = currentUser.username
	# nuevo >>
	result = fun_rearranque(request, "T")
	if result['ok']:
		return result['response']
	activate_language(request)
	if currentUser.id == dd['idJugador1']:
		numJugador = 1
		strOtroJugador = "2"
	else:
		numJugador = 2
		strOtroJugador = "1"
	partido_existe = True
	doble = 0
	try:
		partido = Partido_enJuego.objects.get(tipo="T", idTorneo=dd['idTorneo'], nFaseTorneo=dd['fase'], estadoTorneo=strOtroJugador, jugador1=currentUser)
		# busca el primer partido enJuego que cumple las condiciones
		# los estados en caso de torneo son: "0": sin jugadores, "1": jugador 1 dentro, "2": jugador 2 dentro, "A": ambos jugadores dentro
	except Partido_enJuego.DoesNotExist:
		doble = doble + 1
	try:
		partido = Partido_enJuego.objects.get(tipo="T", idTorneo=dd['idTorneo'], nFaseTorneo=dd['fase'], estadoTorneo=strOtroJugador, jugador2=currentUser)
		# busca el primer partido enJuego que cumple las condiciones
		# los estados en caso de torneo son: "0": sin jugadores, "1": jugador 1 dentro, "2": jugador 2 dentro, "A": ambos jugadores dentro
	except Partido_enJuego.DoesNotExist:
		doble = doble + 1
	if doble >= 2:
		partido_existe = False
	if partido_existe: #
		t2 = datetime.datetime.now()
		s1 = datetime.timedelta(seconds=1)
		partido.estadoTorneo = "A" # ambos jugadores dentro
		partido.empezado = True
		partido.comienzo = t2
		partido.pausa = True
		partido.finDePausa = t2 + s1
		partido.pelota_velocidad_y = pelota_velocidad_c
		partido.pelota_velocidad_x = pelota_velocidad_c
		partido.save()
		idPartido = partido.id
	else:
		if (dd['fase'] > numero_fases(dd['idTorneo']) or player_has_played(IDE, dd['idTorneo'], dd['fase'])):
			return JsonResponse({'caca': 'chupi'})
		partido = Partido_enJuego() #crea nuevo partido (sin arrancar) y coloca el primer jugador
		partido.setDateTimes()
		partido.tipo = "T"
		partido.idTorneo = dd['idTorneo']
		partido.nFaseTorneo = dd['fase']
		partido.estadoTorneo = str(numJugador)		
		partido.limiteTiempoTorneo = dd['limiteTiempoTorneo']
		partido.limiteTiempoConUnJugador = dd['limiteTiempoConUnJugador']
		partido.jugador1 = User.objects.get(id=dd['idJugador1'])
		partido.jugador2 = User.objects.get(id=dd['idJugador2'])
		partido.save()
		idPartido = partido.id
	myLanguage = request.session.get('myLanguage')
	if myLanguage is None:
		myLanguage = request.LANGUAGE_CODE
	mycontext = {
		'idPartido': idPartido,
		'numJugador': numJugador, # 1: izq, 2: der
		'myLanguage': myLanguage,
		'limiteHoraPartido': dd['limiteTiempoTorneo'],
	}
	# numJugador: 1 = izq, 2 = der
	return render(request, 'partidos/pantallaPong_t.html', mycontext)
	
def fun_arranque_rapido(request): # arranque de partido rápido
	if not request.user.is_authenticated:
		return redirect('home')
	# nuevo >>
	result = fun_rearranque(request, "R")
	if result['ok']:
		return result['response']
	# << nuevo
	activate_language(request)
	currentUser = request.user
	idJugador = currentUser.id
	while True:
		partidoConUnJugador = True
		partidos = Partido_enJuego.objects.filter(tipo="R", empezado=False, desconectado=False) 
		# busca el primer partido rápido, no empezado y no desconectado
		# que es lo mismo que un partido rápido con un jugador (el 1 a la izq)
		if partidos:
			partido = partidos[0]
		else:
			partidoConUnJugador = False
			break # no hay partido rápido con un jugador
		if partidoConUnJugador:
			t2 = datetime.datetime.now()
			t1 = partido.pelota_actualizacion
			s = diffTimeSec(t1, t2)
			if s > 2: # si no se actualiza la pelota debe ser por desconexion
				partido.desconectado = True
				partidoConUnJugador = False # este partido no es ya que lo acabo de desconectar, puede ser el siguiente del while
				partido.save()
			else:
				break # encontrado partido rápido con un jugador
	# hay dos casos partido rápido con un jugador encontrado o no
	if partidoConUnJugador: # se encontró un partido rápido sin empezar -- con un solo jugador
		t2 = datetime.datetime.now()
		s1 = datetime.timedelta(seconds=1)
		partido.jugador2 = currentUser # se coloca el segundo jugador y se arranca
		partido.empezado = True
		partido.comienzo = t2
		partido.pausa = True
		partido.finDePausa = t2 + s1
		partido.pelota_velocidad_y = pelota_velocidad_c
		partido.pelota_velocidad_x = pelota_velocidad_c
		partido.save()
		idPartido = partido.id
		numJugador = 2
	else:
		partido = Partido_enJuego() #crea nuevo partido (sin arrancar) y coloca el primer jugador
		partido.tipo = "R" # rápido
		partido.setDateTimes()
		partido.jugador1 = currentUser # se coloca el primer jugador
		partido.save()
		idPartido = partido.id
		numJugador = 1
	myLanguage = request.session.get('myLanguage')
	if myLanguage is None:
		myLanguage = request.LANGUAGE_CODE
	mycontext = {
		'idPartido': idPartido,
		'numJugador': numJugador, # 1: izq, 2: der
		'myLanguage': myLanguage,
		'limiteHoraPartido': '',
	}
	return render(request, 'partidos/pantallaPong_t.html', mycontext)
	# enviar el html-javascript que atiende el partido cambiando idPartido, numJugador

def partidos_mlist(request):
	activate_language(request)
	if not request.user.is_authenticated:
		return redirect('home')
	user = request.user
	partidos2 = Partido_historia.objects.filter(Q(jugador1=user) | Q(jugador2=user)).annotate(duracion=F('fin') - F('comienzo')).order_by('-comienzo')
	context = {'partidos': partidos2, }
	return render(request, 'partidos/partidos_mlist_t.html', context)

def partidos_list(request):
	activate_language(request)
	if not request.user.is_authenticated:
		return redirect('home')
	partidos2 = Partido_historia.objects.all().annotate(duracion=F('fin') - F('comienzo')).order_by('-comienzo')
	context = {'partidos': partidos2, }
	return render(request, 'partidos/partidos_list_t.html', context)
