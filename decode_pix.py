# decode_pix.py
from pix.decoder import detalhar_qrcode_pix
from pix.qrcode_generator import gerar_qr_code_arquivo

if __name__ == '__main__':
    pixcopiaecola = '00020101021226900014BR.GOV.BCB.PIX2568qrcodespix-h.sejaefi.com.br/v2/cobv/eb34b1f05740459b9c19b09624713eef5204000053039865802BR5905EFISA6008SAOPAULO62070503***6304612C'
    result= gerar_qr_code_arquivo(pixcopiaecola)
    # result = detalhar_qrcode_pix(pixcopiaecola)

    # print('Resultado da decodificação:')
    # for k, v in result.items():
    #     print(f'{k}: {v}')
