from .....layers.protocol_messages.protocolentities.attributes.attributes_downloadablemedia import \
    DownloadableMediaMessageAttributes

from .....common.tools import AudioTools
import os
import requests
from pathlib import Path
from zowsuplib.settings.conf import settings
import random

class AudioAttributes(object):
    def __init__(self, downloadablemedia_attributes, seconds, ptt, streaming_sidecar=None, waveform=None):
        # type: (DownloadableMediaMessageAttributes, int, bool, bytes, bytes) -> None
        """
        :param seconds: duration of audio playback in seconds
        :param ptt: indicates whether this is a push-to-talk audio message
        :param streaming_sidecar
        :param waveform: waveform data for audio visualization (bytes array, typically 100 bytes)
        """
        self._downloadablemedia_attributes = downloadablemedia_attributes
        self._seconds = seconds  # type: int
        self._ptt = ptt  # type: bool
        self._streaming_sidecar = streaming_sidecar  # type: bytes
        self._waveform = waveform  # type: bytes

    def __str__(self):
        attrs = []
        if self.seconds is not None:
            attrs.append(("seconds", self.seconds))
        if self.ptt is not None:
            attrs.append(("ptt", self.ptt))
        if self._streaming_sidecar is not None:
            attrs.append(("streaming_sidecar", "[binary data]"))
        if self._waveform is not None:
            attrs.append(("waveform", f"[{len(self._waveform)} bytes]"))
        attrs.append(("downloadable", self.downloadablemedia_attributes))

        return "[%s]" % " ".join((map(lambda item: "%s=%s" % item, attrs)))

    @property
    def downloadablemedia_attributes(self):
        return self._downloadablemedia_attributes

    @downloadablemedia_attributes.setter
    def downloadablemedia_attributes(self, value):
        self._downloadablemedia_attributes = value

    @property
    def seconds(self):
        return self._seconds

    @seconds.setter
    def seconds(self, value):
        self._seconds = value

    @property
    def ptt(self):
        return self._ptt

    @ptt.setter
    def ptt(self, value):
        self._ptt = value

    @property
    def streaming_sidecar(self):
        return self._streaming_sidecar

    @streaming_sidecar.setter
    def streaming_sidecar(self, value):
        self._streaming_sidecar = value

    @property
    def waveform(self):
        return self._waveform

    @waveform.setter
    def waveform(self, value):
        self._waveform = value


    @staticmethod
    def generate_waveform():
        """
        Gera um waveform aleatório baseado em templates pré-definidos.
        Similar ao comportamento do whatsmeow, seleciona um template aleatório
        e modifica ~30% dos bytes aleatoriamente.
        
        Returns:
            bytes: Array de 100 bytes representando o waveform
        """
        # Templates de waveform pré-definidos (baseados no código Go fornecido)
        waveforms = [
            [249, 221, 2, 102, 248, 229, 211, 45, 117, 106, 107, 213, 221, 10, 139, 146, 161, 117, 202, 35, 53, 71, 98, 183, 189, 170, 188, 187, 174, 29, 209, 188, 253, 200, 5, 56, 31, 232, 152, 65, 147, 137, 234, 85, 47, 110, 61, 191, 30, 243, 202, 71, 29, 2, 142, 201, 30, 195, 130, 71, 61, 5, 90, 198, 35, 208, 164, 210, 185, 253, 221, 40, 128, 43, 14, 13, 76, 126, 118, 225, 2, 253, 83, 104, 72, 28, 141, 87, 71, 227, 207, 105, 16, 28, 111, 67, 21, 95, 146, 106],
            [207, 79, 199, 5, 7, 82, 116, 174, 55, 147, 248, 156, 25, 116, 43, 239, 145, 108, 6, 10, 231, 235, 36, 242, 155, 226, 99, 41, 195, 248, 108, 145, 39, 55, 79, 234, 63, 238, 213, 230, 157, 101, 54, 70, 85, 69, 168, 174, 91, 183, 212, 238, 232, 128, 48, 189, 91, 215, 213, 130, 210, 105, 23, 23, 12, 148, 191, 6, 49, 16, 201, 7, 122, 32, 69, 123, 84, 108, 248, 251, 193, 5, 119, 139, 222, 204, 6, 34, 29, 79, 87, 55, 102, 18, 19, 123, 176, 176, 116, 59],
            [33, 186, 143, 170, 23, 6, 35, 215, 103, 106, 147, 137, 112, 128, 156, 190, 158, 203, 200, 92, 246, 130, 14, 84, 231, 122, 108, 16, 194, 252, 32, 187, 107, 95, 19, 190, 69, 29, 8, 207, 245, 71, 97, 134, 158, 175, 90, 62, 28, 74, 189, 81, 210, 15, 178, 157, 150, 149, 111, 73, 120, 72, 254, 234, 36, 204, 123, 104, 255, 183, 6, 147, 236, 211, 57, 42, 35, 5, 191, 106, 58, 17, 47, 148, 7, 134, 209, 72, 237, 89, 114, 150, 213, 141, 120, 25, 225, 32, 201, 114],
            [135, 59, 36, 38, 48, 14, 24, 28, 69, 221, 52, 26, 242, 163, 120, 117, 127, 161, 171, 189, 24, 219, 43, 143, 111, 106, 164, 83, 147, 91, 248, 123, 56, 122, 130, 241, 230, 20, 209, 198, 62, 239, 229, 127, 196, 125, 189, 14, 246, 134, 42, 43, 47, 6, 124, 24, 206, 143, 41, 18, 206, 46, 140, 214, 89, 3, 95, 6, 144, 54, 83, 218, 206, 28, 53, 189, 192, 185, 245, 141, 113, 50, 222, 142, 246, 45, 44, 233, 60, 233, 66, 70, 86, 209, 78, 54, 87, 127, 72, 92],
            [89, 157, 62, 124, 147, 97, 2, 150, 242, 133, 118, 180, 169, 237, 10, 17, 211, 161, 161, 162, 245, 91, 243, 86, 194, 248, 63, 129, 11, 63, 209, 67, 84, 252, 53, 252, 19, 44, 88, 42, 111, 172, 81, 129, 37, 147, 97, 238, 237, 209, 173, 211, 156, 104, 82, 222, 103, 216, 242, 126, 65, 204, 253, 210, 165, 15, 122, 228, 59, 117, 10, 159, 175, 130, 171, 58, 35, 5, 241, 49, 72, 94, 131, 130, 84, 237, 152, 62, 7, 119, 106, 234, 89, 35, 76, 139, 132, 26, 84, 170],
            [109, 254, 35, 233, 37, 217, 181, 122, 209, 107, 150, 246, 52, 243, 91, 105, 70, 43, 249, 171, 20, 169, 85, 114, 197, 99, 224, 75, 1, 4, 199, 33, 200, 183, 131, 152, 79, 55, 95, 10, 204, 15, 142, 0, 134, 7, 11, 204, 103, 245, 168, 238, 197, 23, 6, 116, 56, 136, 105, 76, 4, 107, 83, 54, 193, 117, 212, 79, 244, 148, 217, 217, 63, 127, 49, 56, 16, 242, 64, 51, 226, 112, 182, 233, 7, 199, 133, 33, 206, 126, 56, 35, 165, 190, 96, 230, 152, 120, 1, 138],
            [149, 140, 254, 15, 5, 187, 82, 170, 120, 151, 246, 129, 83, 252, 144, 127, 15, 12, 51, 246, 2, 4, 16, 223, 156, 190, 224, 86, 109, 187, 11, 71, 76, 147, 152, 230, 211, 144, 100, 42, 219, 78, 186, 100, 18, 244, 193, 130, 38, 58, 228, 27, 186, 141, 10, 62, 16, 124, 64, 255, 205, 100, 168, 250, 129, 140, 23, 227, 81, 140, 178, 164, 53, 118, 148, 220, 81, 243, 4, 122, 42, 99, 203, 4, 86, 155, 163, 207, 120, 8, 152, 32, 244, 219, 217, 226, 113, 149, 176, 183],
            [26, 78, 203, 92, 116, 186, 21, 231, 203, 147, 44, 126, 231, 170, 176, 150, 49, 1, 177, 78, 80, 131, 32, 180, 136, 190, 252, 220, 116, 116, 127, 226, 58, 71, 52, 52, 149, 156, 33, 102, 30, 15, 85, 190, 192, 2, 109, 210, 205, 133, 27, 131, 235, 121, 35, 153, 77, 228, 106, 169, 26, 173, 123, 200, 71, 169, 239, 182, 6, 24, 99, 138, 218, 4, 96, 196, 250, 1, 217, 64, 171, 150, 195, 250, 83, 149, 38, 176, 163, 166, 127, 109, 95, 240, 194, 5, 237, 247, 242, 68],
            [149, 165, 47, 252, 245, 239, 238, 220, 15, 58, 121, 126, 188, 76, 71, 81, 4, 110, 89, 54, 26, 188, 230, 85, 18, 70, 122, 45, 37, 34, 63, 58, 243, 178, 166, 195, 204, 208, 76, 21, 136, 47, 243, 1, 65, 170, 223, 11, 97, 230, 74, 89, 120, 186, 234, 140, 213, 110, 166, 165, 197, 226, 193, 246, 189, 1, 38, 85, 49, 223, 46, 73, 180, 197, 50, 41, 124, 30, 103, 54, 56, 94, 226, 178, 83, 206, 148, 55, 179, 145, 226, 67, 249, 2, 10, 118, 126, 121, 192, 52],
            [70, 164, 150, 93, 212, 174, 207, 105, 47, 8, 126, 254, 73, 223, 97, 92, 71, 28, 102, 176, 85, 9, 16, 12, 74, 169, 47, 100, 35, 172, 109, 50, 9, 179, 174, 148, 250, 169, 125, 157, 47, 182, 144, 97, 82, 176, 83, 190, 105, 254, 134, 181, 215, 41, 43, 43, 70, 214, 180, 97, 150, 9, 183, 72, 182, 186, 45, 253, 141, 44, 177, 32, 204, 93, 136, 161, 134, 82, 27, 71, 157, 53, 128, 163, 28, 60, 94, 204, 222, 98, 231, 86, 26, 170, 108, 158, 163, 251, 205, 19],
        ]
        
        # Seleciona um template aleatório (igual ao código Go: rand.Intn(len(waveforms)))
        chosen_index = random.randint(0, len(waveforms) - 1)
        selected_waveform = waveforms[chosen_index].copy()  # Cria uma cópia para modificar
        
        # Calcula quantos elementos modificar (~30% do tamanho)
        # Igual ao código Go: int(float64(len(selectedWaveform)) * 0.3)
        num_elements_to_change = int(len(selected_waveform) * 0.3)
        
        # Modifica os bytes aleatoriamente
        # Igual ao código Go: byte(rand.Intn(251) + 3) -> valores entre 3 e 253
        for i in range(num_elements_to_change):
            random_index = random.randint(0, len(selected_waveform) - 1)
            selected_waveform[random_index] = random.randint(3, 253)
        
        return bytes(selected_waveform)

    @staticmethod
    def from_filepath(filepath,mediaType=None,resultRequestMediaConnIqProtocolEntity=None, 
        audioPropertis=None, ptt=False,streaming_sidecar=None, waveform=None):
        assert os.path.exists(filepath)
        audioPropertis = audioPropertis or AudioTools.getAudioProperties(filepath)
        seconds= audioPropertis if audioPropertis else None
        
        # Se waveform não foi fornecido e é PTT, gera um waveform aleatório
        if waveform is None and ptt:
            waveform = AudioAttributes.generate_waveform()
        
        return AudioAttributes(
            DownloadableMediaMessageAttributes.from_file(filepath,mediaType,resultRequestMediaConnIqProtocolEntity), 
            seconds, ptt, streaming_sidecar, waveform
        )
    

    @staticmethod
    def from_url(url,mediaType=None,resultRequestMediaConnIqProtocolEntity=None, 
        audioPropertis=None, ptt=False,streaming_sidecar=None, waveform=None):

        down_res = requests.get(url=url)
        filename = url[url.rfind("/",0):]
        download_dir = Path(settings.download_path)
        filepath = str(download_dir / filename)
        with open(filepath,"wb") as file:
            file.write(down_res.content)       

        audioPropertis = audioPropertis or AudioTools.getAudioProperties(filepath)
        seconds= audioPropertis if audioPropertis else None
        
        # Se waveform não foi fornecido e é PTT, gera um waveform aleatório
        if waveform is None and ptt:
            waveform = AudioAttributes.generate_waveform()
        
        return AudioAttributes(
            DownloadableMediaMessageAttributes.from_file(filepath,mediaType,resultRequestMediaConnIqProtocolEntity), 
            seconds, ptt, streaming_sidecar, waveform
        )    

