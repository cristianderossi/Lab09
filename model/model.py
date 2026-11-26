from database.parco_DAO import ParcoDAO
from database.escursione_DAO import EscursioneDAO
from database.punto_interesse_DAO import PuntoInteresseDAO


class Model:
    def __init__(self):
        self.escursioni_map = {} # Mappa ID escursione -> oggetti Escursione
        self.punti_interesse_map = {} # Mappa ID punto di interesse -> oggetti PuntoInteresse

        self._pacchetto_ottimo = []
        self._valore_ottimo: int = -1
        self._costo = 0

        # Altri attributi
        self._max_giorni = None           # vincolo sui giorni (None = nessun limite)
        self._max_budget = None           # vincolo sul budget (None = nessun limite)
        self._escursione_parchi = []      # escursioni del parco selezionato

        # Caricamento
        self.load_escursioni()
        self.load_punti_interesse()
        self.load_relazioni()

    @staticmethod
    def load_parchi():
        """ Restituisce tutti i parchi disponibili """
        return ParcoDAO.get_parchi()

    def load_escursioni(self):
        """ Carica tutte le escursioni in un dizionario [id, Escursione]"""
        self.escursioni_map = EscursioneDAO.get_escursioni()

    def load_punti_interesse(self):
        """ Carica tutti i punti di interesse in un dizionario [id, PuntoInteresse]"""
        self.punti_interesse_map = PuntoInteresseDAO.get_punti_interesse()

    def load_relazioni(self):
        """
            Interroga il database per ottenere tutte le relazioni fra escursioni e punti di interesse e salvarle nelle strutture dati
            Collega escursione <-> punti di interesse.
            --> Ogni Escursione ha un set di PuntoInteresse.
            --> Ogni PuntoInteresse ha un set di Escursioni.
        """
        relazioni = EscursioneDAO.get_escursioni_punti_interesse()

        if relazioni is None:
            return

        for relazione in relazioni:
            escursione = self.escursioni_map[relazione["id_escursione"]]
            punto = self.punti_interesse_map[relazione["id_punto_interesse"]]

            escursione.punti_interesse.add(punto)
            punto.escursioni.add(escursione)

    def genera_pacchetto(self, id_parco: str, max_giorni: int = None, max_budget: float = None):
        """
        Calcola il pacchetto di escursioni ottimale per un parco rispettando i vincoli di durata, budget e punti di interesse unici.
        :param id_parco: id del parco
        :param max_giorni: numero massimo di giorni (può essere None --> nessun limite)
        :param max_budget: costo massimo del pacchetto (può essere None --> nessun limite)

        :return: self._pacchetto_ottimo (una lista di oggetti Escursione)
        :return: self._costo (il costo del pacchetto)
        :return: self._valore_ottimo (il voto complessivo dei visitatori per il pacchetto)
        """
        self._pacchetto_ottimo = []
        self._costo = 0
        self._valore_ottimo = -1

        self._max_giorni = max_giorni
        self._max_budget = max_budget

        # Tengo solo le escursioni del parco selezionato
        self._escursione_parchi = []
        for escursione in self.escursioni_map.values():
            if escursione.id_parco == id_parco:
                self._escursione_parchi.append(escursione)

        # Avvio della ricorsione: indice 0, pacchetto vuoto, 0 giorni, 0 €, voto 0, nessun punto usato
        self._ricorsione(0, [], 0, 0, 0, set())

        return self._pacchetto_ottimo, self._costo, self._valore_ottimo

    def _ricorsione(self, start_index: int, pacchetto_parziale: list, durata_corrente: int, costo_corrente: float, valore_corrente: int, punti_usati: set):
        """ Algoritmo di ricorsione che deve trovare il pacchetto che massimizza il voto complessivo dei visitatori"""

        # A - il pacchetto attuale è il migliore trovato finora?
        if valore_corrente > self._valore_ottimo:
            self._valore_ottimo = valore_corrente
            self._pacchetto_ottimo = pacchetto_parziale.copy()
            self._costo = costo_corrente

        for indice in range(start_index, len(self._escursione_parchi)):
            escursione = self._escursione_parchi[indice]

            # C - vincoli: se uno non è rispettato salto questa escursione
            if self._max_giorni is not None and durata_corrente + escursione.durata_giorni > self._max_giorni:
                continue
            if self._max_budget is not None and costo_corrente + escursione.costo > self._max_budget:
                continue
            if not punti_usati.isdisjoint(escursione.punti_interesse):
                continue

            # D - aggiungo l'escursione e calcolo il suo voto
            pacchetto_parziale.append(escursione)
            voto_escursione = 0
            for punto in escursione.punti_interesse:
                voto_escursione += punto.voto_visitatori

            # E - ricorsione sulle escursioni successive
            self._ricorsione(indice + 1,
                             pacchetto_parziale,
                             durata_corrente + escursione.durata_giorni,
                             costo_corrente + escursione.costo,
                             valore_corrente + voto_escursione,
                             punti_usati | escursione.punti_interesse)

            # F - backtracking
            pacchetto_parziale.pop()