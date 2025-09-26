import requests
import jwt
import pytz
from datetime import timedelta, datetime, timezone, date

# converte uma string no formato ISO 8601 para um objeto datetime em UTC.
# Se a string for só data (YYYY-MM-DD), trata como meia-noite UTC desse dia.
# Essa def é necessária porque o retorno do payload do pix é em ISO 8601.
def converte_iso_datetime_utc(iso_str):
	# Caso seja só data (YYYY-MM-DD)
	if len(iso_str) == 10 and iso_str.count("-") == 2: # Só data -> meia-noite UTC
		dt = date.fromisoformat(iso_str)  # objeto date
		dt = datetime(dt.year, dt.month, dt.day, tzinfo=pytz.UTC)  # datetime UTC
		return dt

	# Se tiver hora (ISO completo)
	dt = date.fromisoformat(iso_str)  # isso já cria em UTC se não tiver tz
	if dt.tzinfo is None:
		dt = pytz.UTC.localize(dt) # Se não tem tzinfo, assumimos que já está em UTC
	else:
		dt = dt.astimezone(pytz.UTC) # Se tem timezone, convertemos para UTC

	return dt # exemplo de retorno: 2025-09-04 12:00:00+00:00


def detalhar_qrcode_pix(codigo_pix):
#     Foquei no retorno do valor, nome, txid, a data de criação, expiração e vencimento porque foi o que precisei, mas você pode puxar quais dados quiser

	if not codigo_pix:
		return
	# Um pix funciona da seguinte forma: tag tamanho valor
	# Nesse dicionário adicionamos todas as tags
	TAGS = {
		'00': 'payload_format_indicator',
		'26': 'merchant_account_information',  # Em qr code estático a chave pix é a subtag 01. Em Qr code dinâmico está no arquivo da url.
		'52': 'merchant_category_code',
		'53': 'transaction_currency',
		'54': 'transaction_amount', # Em qr code estático é opcional. Em qr code dinâmico obrigatório mas pode estar apenas no arquivo da url.
		'58': 'country_code',
		'59': 'merchant_name',
		'60': 'merchant_city',
		'62': 'additional_data_field_template',  # Em qr code estático o TXID está na subtag 05. Em Qr code dinâmico está no arquivo da url.
		'63': 'crc16'
	}

	data = {}
	index = 0

	# Processamento do payload principal
	while index < len(codigo_pix):
		if index + 4 > len(codigo_pix):  # Se tem uma tag mas não tem tamanho e nem valor o qr code é inválido
			print(f'QR Code inválido. Tamanho insuficiente')

		tag = codigo_pix[index:index+2]  # Separamos a tag
		length_str = codigo_pix[index+2:index+4]  # Separamos o tamanho da tag

		if not length_str.isdigit():  # Se os caracteres de tamanho não são compostos apenas por numeros
			print(f'QR Code inválido. Certifique-se que nenhum caracter foi modificado')

		length = int(length_str)

		if index + 4 + length > len(codigo_pix):  # Se o tamanho de uma tag não corresponder com o valor
			print(f'QR Code inválido. Dados incompletos. Certifique-se de que não há caracteres ausentes.')

		value = codigo_pix[index+4:index+4+length]
		data[TAGS.get(tag, tag)] = value
		index += 4 + length

	# Verifica campos obrigatórios
	if 'merchant_account_information' not in data or 'merchant_name' not in data:
		print(f'Pix inválido. Campos obrigatórios faltando. Certifique-se de que não há caracteres ausentes.')

	# Processamento do merchant_account_information (tag 26)
	# também identificamos se é qr code dinâmico ou estático
	chave_pix = None
	is_dynamic = False
	url = None
	valor = None
	vencimento = None
	criacao = None
	expira_qrcode = None
	merchant_info = data['merchant_account_information']

	i = 0
	while i < len(merchant_info):
		if i + 4 > len(merchant_info):
			break

		subtag = merchant_info[i:i+2]
		sublength_str = merchant_info[i+2:i+4]

		if not sublength_str.isdigit():
			break

		sublength = int(sublength_str)

		if i + 4 + sublength > len(merchant_info):
			break

		if subtag == '25':  # URL do Payload para pix dinâmico
			url = merchant_info[i+4:i+4+sublength]
			is_dynamic = True
			break
		elif subtag == "01":  # Se não tiver a subtag 01 não há chave pix, então o qr code não será válido para pagamento direto, o app bancário provavelmente mostrará erro
			chave_pix = merchant_info[i+4:i+4+sublength]
			break

		i += 4 + sublength

	# Processamento do additional_data_field_template (tag 62)
	txid = None

	if is_dynamic == False:	# qr code estático, logo o txid está no pix copia e cola
		if 'additional_data_field_template' in data:
			additional_info = data['additional_data_field_template']
			i = 0
			while i < len(additional_info):
				if i + 4 > len(additional_info):
					break

				subtag = additional_info[i:i+2]
				sublength_str = additional_info[i+2:i+4]

				if not sublength_str.isdigit():
					break

				sublength = int(sublength_str)

				if i + 4 + sublength > len(additional_info):
					break

				if subtag == "05":  # Subtag 05 = TXID
					txid = additional_info[i+4:i+4+sublength]
					break

				i += 4 + sublength

		if 'transaction_amount' in data:	# Caso o valor não esteja no pix copia e cola, o usuário deve informar algum
			valor = round(data.get('transaction_amount'), 2)

	else: # qr code dinâmico, logo txid, chave e valor estão dentro do arquivo da url
		try:
			response = requests.get('https://' + url) # baixa o arquivo da url
			base64_string = response.text.strip()	# pega a string
			json_data = jwt.decode(base64_string, options={'verify_signature': False})	# decodifica a string e já deixa na forma de dicionário

			# Tratamentos para pix pagamento imediato e pix com vencimento
			timestamp_criacao =  json_data.get('calendario', {}).get('criacao', None)
			if timestamp_criacao is not None:
				criacao = converte_iso_datetime_utc(timestamp_criacao)

				# se constar o campo de dataDeVencimento o pix é com vencimento
				data_vencimento = json_data.get('calendario', {}).get('dataDeVencimento', None)

				if data_vencimento is not None:
					vencimento = converte_iso_datetime_utc(data_vencimento)

					expira_qrcode = json_data.get('calendario', {}).get('validadeAposVencimento', None) # número de dias em que a cobrança é válida após o vencimento
					if expira_qrcode is not None:
						expira_qrcode = vencimento + timedelta(days=expira_qrcode)

				# Pix pagamento imediato
				# Se o pix pagamento imediato não tiver o campo de expiração o padrão é 86400 segundos.
				else:
					expira_qrcode = json_data.get('calendario', {}).get('expiracao', 86400)
					expira_qrcode = criacao + timedelta(seconds=expira_qrcode)

			valor = json_data.get('valor', {}).get('original', None)
			if valor is not None:
				valor = round(valor, 2) # O ideal é que aqui, você adicione alguma forma de arredondamento

			chave_pix = json_data.get('chave', None)
			txid = json_data.get('txid', None)

		except Exception as e:
			print(f'Erro ao detalhar QR Code. Certifique-se de que o pix copia e cola informado não expirou.')

	if expira_qrcode and expira_qrcode < datetime.now(timezone.utc):
		print(f'O pix copia e cola informado já expirou.')

	if is_dynamic == False and chave_pix == None:
		print(f'Sem chave pix o QR Code não é válido para pagamentos diretos.')

	try:
		# Resultado final
		resultado = {
			'chave': chave_pix,
			'valor': valor,
			'nome': data.get("merchant_name"),
			'txid': txid,
			'criacao_qrcode': criacao, # Dica: O MySQL, por padrão, não aceita offset de timezone em colunas do tipo DATETIME, por isso o astimezone(pytz.UTC).replace(tzinfo=None)
			'expira_qrcode': expira_qrcode, # o astimezone(pytz.UTC).replace(tzinfo=None) mantém o valor correto (UTC) mas remove o offset, e MySQL aceita.
			'data_vencimento': vencimento
		}
		return resultado

	except Exception as e:
		print(f'Erro ao processar QR Code. {str(e)}')
