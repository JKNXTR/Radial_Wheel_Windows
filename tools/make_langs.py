"""Генерира lang_<код>.json за допълнителните езици (основни текстове; останалото пада към английски)."""
import json
from pathlib import Path

KEYS = """tray.show tray.settings tray.exit tray.close
sector.keyboard sector.folders sector.system sector.favorites sector.sound sector.internet sector.settings sector.programs
center.delete
panel.quick_keys panel.std_keyboard panel.win_keys panel.folders panel.programs panel.settings panel.internet panel.sound panel.system panel.favorites
sub.browsers sub.google sub.sites sub.volume sub.devices
folder.documents folder.pictures folder.music folder.videos folder.projects folder.downloads folder.archive folder.system
app.browser app.editor app.player app.calculator app.graphics app.mail app.games app.notes
sys.start sys.taskmgr sys.settings sys.lock sys.sleep sys.restart sys.shutdown sys.run sys.confirm_restart sys.confirm_shutdown
fav.add search.button search.placeholder
ctx.choose_file ctx.choose_folder ctx.reset ctx.remove
btn.file btn.folder btn.clear
tip.Screenshot tip.Copy tip.Paste tip.Back tip.Forward tip.Undo""".split()

# 70 реда на език, в реда на KEYS (разделител |)
T = {
"de": ("Rad öffnen|Einstellungen…|Komplett beenden|Schließen (Hotkey startet neu)|Tastatur|Ordner|Windows-Befehle|Favoriten|Ton|Internet|Einstellungen|Programme|Entf|"
"Schnelle Tastaturbefehle|Standardtastatur|Haupt- und Windows-Sondertasten|Verzeichnisse und Ordner|Programme und Anwendungen|Rad-Einstellungen|Internet und Browsen|Toneinstellungen|Windows-Systembefehle|Favoriten und Schnellzugriff|"
"Browser wählen|Google-Suche|Gespeicherte Seiten|Lautstärke|Wiedergabegeräte|Dokumente|Bilder|Musik|Videos|Projekte|Downloads|Archiv|System|Browser|Editor|Player|Rechner|Grafik|E-Mail|Spiele|Notizen|"
"Start|Task-Manager|Einstellungen|Sperren|Standby|Neustart|Herunterfahren|Ausführen|Computer neu starten?|Computer herunterfahren?|Hinzufügen|Suchen|Google durchsuchen…|"
"Datei / Programm wählen…|Ordner wählen…|Standard wiederherstellen|Slot entfernen|Datei…|Ordner…|Leeren|Screenshot (Umschalt+Win+S)|Kopieren (Strg+C)|Einfügen (Strg+V)|Zurück (Alt+←)|Vorwärts (Alt+→)|Rückgängig (Strg+Z)"),
"fr": ("Ouvrir la roue|Paramètres…|Quitter complètement|Fermer (le raccourci relance)|Clavier|Dossiers|Commandes Windows|Favoris|Son|Internet|Paramètres|Programmes|Suppr|"
"Commandes clavier rapides|Clavier standard|Touches principales et Windows|Répertoires et dossiers|Programmes et applications|Paramètres de la roue|Internet et navigation|Paramètres du son|Commandes système Windows|Favoris et accès rapide|"
"Choisir le navigateur|Recherche Google|Sites enregistrés|Volume|Périphériques de lecture|Documents|Images|Musique|Vidéos|Projets|Téléchargements|Archives|Système|Navigateur|Éditeur|Lecteur|Calculatrice|Graphisme|Courrier|Jeux|Notes|"
"Démarrer|Gest. tâches|Paramètres|Verrouiller|Veille|Redémarrer|Arrêter|Exécuter|Redémarrer l’ordinateur ?|Arrêter l’ordinateur ?|Ajouter|Rechercher|Rechercher sur Google…|"
"Choisir un fichier / programme…|Choisir un dossier…|Rétablir par défaut|Supprimer l’emplacement|Fichier…|Dossier…|Effacer|Capture d’écran (Maj+Win+S)|Copier (Ctrl+C)|Coller (Ctrl+V)|Précédent (Alt+←)|Suivant (Alt+→)|Annuler (Ctrl+Z)"),
"es": ("Abrir la rueda|Ajustes…|Salir por completo|Cerrar (el atajo lo reinicia)|Teclado|Carpetas|Comandos de Windows|Favoritos|Sonido|Internet|Ajustes|Programas|Supr|"
"Comandos rápidos de teclado|Teclado estándar|Teclas principales y de Windows|Directorios y carpetas|Programas y aplicaciones|Ajustes de la rueda|Internet y navegación|Ajustes de sonido|Comandos del sistema Windows|Favoritos y acceso rápido|"
"Elegir navegador|Búsqueda en Google|Sitios guardados|Volumen|Dispositivos de reproducción|Documentos|Imágenes|Música|Vídeos|Proyectos|Descargas|Archivo|Sistema|Navegador|Editor|Reproductor|Calculadora|Gráficos|Correo|Juegos|Notas|"
"Inicio|Administrador|Ajustes|Bloquear|Suspender|Reiniciar|Apagar|Ejecutar|¿Reiniciar el equipo?|¿Apagar el equipo?|Añadir|Buscar|Buscar en Google…|"
"Elegir archivo / programa…|Elegir carpeta…|Restaurar valor|Quitar ranura|Archivo…|Carpeta…|Borrar|Captura (Mayús+Win+S)|Copiar (Ctrl+C)|Pegar (Ctrl+V)|Atrás (Alt+←)|Adelante (Alt+→)|Deshacer (Ctrl+Z)"),
"it": ("Apri la ruota|Impostazioni…|Esci completamente|Chiudi (la scorciatoia la riavvia)|Tastiera|Cartelle|Comandi Windows|Preferiti|Audio|Internet|Impostazioni|Programmi|Canc|"
"Comandi rapidi da tastiera|Tastiera standard|Tasti principali e Windows|Directory e cartelle|Programmi e applicazioni|Impostazioni della ruota|Internet e navigazione|Impostazioni audio|Comandi di sistema Windows|Preferiti e accesso rapido|"
"Scegli browser|Ricerca Google|Siti salvati|Volume|Dispositivi di riproduzione|Documenti|Immagini|Musica|Video|Progetti|Download|Archivio|Sistema|Browser|Editor|Lettore|Calcolatrice|Grafica|Posta|Giochi|Note|"
"Start|Gest. attività|Impostazioni|Blocca|Sospendi|Riavvia|Arresta|Esegui|Riavviare il computer?|Arrestare il computer?|Aggiungi|Cerca|Cerca su Google…|"
"Scegli file / programma…|Scegli cartella…|Ripristina predefinito|Rimuovi slot|File…|Cartella…|Svuota|Screenshot (Maiusc+Win+S)|Copia (Ctrl+C)|Incolla (Ctrl+V)|Indietro (Alt+←)|Avanti (Alt+→)|Annulla (Ctrl+Z)"),
"pt": ("Abrir a roda|Definições…|Sair completamente|Fechar (o atalho reinicia)|Teclado|Pastas|Comandos do Windows|Favoritos|Som|Internet|Definições|Programas|Del|"
"Comandos rápidos de teclado|Teclado padrão|Teclas principais e do Windows|Diretórios e pastas|Programas e aplicações|Definições da roda|Internet e navegação|Definições de som|Comandos do sistema Windows|Favoritos e acesso rápido|"
"Escolher navegador|Pesquisa Google|Sites guardados|Volume|Dispositivos de reprodução|Documentos|Imagens|Música|Vídeos|Projetos|Transferências|Arquivo|Sistema|Navegador|Editor|Leitor|Calculadora|Gráficos|Correio|Jogos|Notas|"
"Iniciar|Gest. tarefas|Definições|Bloquear|Suspender|Reiniciar|Desligar|Executar|Reiniciar o computador?|Desligar o computador?|Adicionar|Pesquisar|Pesquisar no Google…|"
"Escolher ficheiro / programa…|Escolher pasta…|Repor predefinição|Remover espaço|Ficheiro…|Pasta…|Limpar|Captura (Shift+Win+S)|Copiar (Ctrl+C)|Colar (Ctrl+V)|Voltar (Alt+←)|Avançar (Alt+→)|Anular (Ctrl+Z)"),
"nl": ("Wiel openen|Instellingen…|Volledig afsluiten|Sluiten (sneltoets start opnieuw)|Toetsenbord|Mappen|Windows-opdrachten|Favorieten|Geluid|Internet|Instellingen|Programma’s|Del|"
"Snelle toetsopdrachten|Standaardtoetsenbord|Hoofd- en Windows-speciaaltoetsen|Mappen en directory’s|Programma’s en toepassingen|Wielinstellingen|Internet en browsen|Geluidsinstellingen|Windows-systeemopdrachten|Favorieten en snelle toegang|"
"Kies browser|Google zoeken|Opgeslagen sites|Volume|Afspeelapparaten|Documenten|Afbeeldingen|Muziek|Video’s|Projecten|Downloads|Archief|Systeem|Browser|Editor|Speler|Rekenmachine|Grafisch|E-mail|Games|Notities|"
"Start|Taakbeheer|Instellingen|Vergrendelen|Slaapstand|Opnieuw starten|Afsluiten|Uitvoeren|Computer opnieuw starten?|Computer afsluiten?|Toevoegen|Zoeken|Zoeken op Google…|"
"Kies bestand / programma…|Kies map…|Standaard herstellen|Slot verwijderen|Bestand…|Map…|Wissen|Schermafbeelding (Shift+Win+S)|Kopiëren (Ctrl+C)|Plakken (Ctrl+V)|Terug (Alt+←)|Vooruit (Alt+→)|Ongedaan maken (Ctrl+Z)"),
"pl": ("Otwórz koło|Ustawienia…|Zamknij całkowicie|Zamknij (skrót uruchomi ponownie)|Klawiatura|Foldery|Polecenia Windows|Ulubione|Dźwięk|Internet|Ustawienia|Programy|Del|"
"Szybkie polecenia klawiatury|Klawiatura standardowa|Klawisze główne i Windows|Katalogi i foldery|Programy i aplikacje|Ustawienia koła|Internet i przeglądanie|Ustawienia dźwięku|Polecenia systemowe Windows|Ulubione i szybki dostęp|"
"Wybierz przeglądarkę|Wyszukiwanie Google|Zapisane strony|Głośność|Urządzenia odtwarzania|Dokumenty|Obrazy|Muzyka|Wideo|Projekty|Pobrane|Archiwum|System|Przeglądarka|Edytor|Odtwarzacz|Kalkulator|Grafika|Poczta|Gry|Notatki|"
"Start|Menedżer zadań|Ustawienia|Zablokuj|Uśpij|Uruchom ponownie|Zamknij system|Uruchom|Uruchomić ponownie komputer?|Wyłączyć komputer?|Dodaj|Szukaj|Szukaj w Google…|"
"Wybierz plik / program…|Wybierz folder…|Przywróć domyślne|Usuń miejsce|Plik…|Folder…|Wyczyść|Zrzut ekranu (Shift+Win+S)|Kopiuj (Ctrl+C)|Wklej (Ctrl+V)|Wstecz (Alt+←)|Dalej (Alt+→)|Cofnij (Ctrl+Z)"),
"cs": ("Otevřít kolo|Nastavení…|Ukončit úplně|Zavřít (zkratka spustí znovu)|Klávesnice|Složky|Příkazy Windows|Oblíbené|Zvuk|Internet|Nastavení|Programy|Del|"
"Rychlé příkazy klávesnice|Standardní klávesnice|Hlavní a speciální klávesy Windows|Adresáře a složky|Programy a aplikace|Nastavení kola|Internet a procházení|Nastavení zvuku|Systémové příkazy Windows|Oblíbené a rychlý přístup|"
"Vybrat prohlížeč|Hledání Google|Uložené stránky|Hlasitost|Přehrávací zařízení|Dokumenty|Obrázky|Hudba|Videa|Projekty|Stažené|Archiv|Systém|Prohlížeč|Editor|Přehrávač|Kalkulačka|Grafika|Pošta|Hry|Poznámky|"
"Start|Správce úloh|Nastavení|Zamknout|Uspat|Restartovat|Vypnout|Spustit|Restartovat počítač?|Vypnout počítač?|Přidat|Hledat|Hledat na Googlu…|"
"Vybrat soubor / program…|Vybrat složku…|Obnovit výchozí|Odebrat pozici|Soubor…|Složka…|Vymazat|Snímek obrazovky (Shift+Win+S)|Kopírovat (Ctrl+C)|Vložit (Ctrl+V)|Zpět (Alt+←)|Vpřed (Alt+→)|Zpět (Ctrl+Z)"),
"ro": ("Deschide roata|Setări…|Ieșire completă|Închide (scurtătura repornește)|Tastatură|Foldere|Comenzi Windows|Favorite|Sunet|Internet|Setări|Programe|Del|"
"Comenzi rapide de tastatură|Tastatură standard|Taste principale și Windows|Directoare și foldere|Programe și aplicații|Setările roții|Internet și navigare|Setări de sunet|Comenzi de sistem Windows|Favorite și acces rapid|"
"Alege browserul|Căutare Google|Site-uri salvate|Volum|Dispozitive de redare|Documente|Imagini|Muzică|Videoclipuri|Proiecte|Descărcări|Arhivă|Sistem|Browser|Editor|Player|Calculator|Grafică|Poștă|Jocuri|Notițe|"
"Start|Manager sarcini|Setări|Blocare|Repaus|Repornire|Oprire|Executare|Reporniți computerul?|Opriți computerul?|Adaugă|Caută|Caută pe Google…|"
"Alege fișier / program…|Alege folder…|Restabilește implicit|Elimină slotul|Fișier…|Folder…|Șterge|Captură de ecran (Shift+Win+S)|Copiere (Ctrl+C)|Lipire (Ctrl+V)|Înapoi (Alt+←)|Înainte (Alt+→)|Anulare (Ctrl+Z)"),
"el": ("Άνοιγμα τροχού|Ρυθμίσεις…|Πλήρης έξοδος|Κλείσιμο (η συντόμευση το ξεκινά ξανά)|Πληκτρολόγιο|Φάκελοι|Εντολές Windows|Αγαπημένα|Ήχος|Διαδίκτυο|Ρυθμίσεις|Προγράμματα|Del|"
"Γρήγορες εντολές πληκτρολογίου|Τυπικό πληκτρολόγιο|Κύρια και ειδικά πλήκτρα Windows|Κατάλογοι και φάκελοι|Προγράμματα και εφαρμογές|Ρυθμίσεις τροχού|Διαδίκτυο και περιήγηση|Ρυθμίσεις ήχου|Εντολές συστήματος Windows|Αγαπημένα και γρήγορη πρόσβαση|"
"Επιλογή προγράμματος περιήγησης|Αναζήτηση Google|Αποθηκευμένοι ιστότοποι|Ένταση|Συσκευές αναπαραγωγής|Έγγραφα|Εικόνες|Μουσική|Βίντεο|Έργα|Λήψεις|Αρχείο|Σύστημα|Περιηγητής|Επεξεργαστής|Αναπαραγωγέας|Αριθμομηχανή|Γραφικά|Αλληλογραφία|Παιχνίδια|Σημειώσεις|"
"Έναρξη|Διαχ. εργασιών|Ρυθμίσεις|Κλείδωμα|Αναστολή|Επανεκκίνηση|Τερματισμός|Εκτέλεση|Επανεκκίνηση του υπολογιστή;|Τερματισμός του υπολογιστή;|Προσθήκη|Αναζήτηση|Αναζήτηση στο Google…|"
"Επιλογή αρχείου / προγράμματος…|Επιλογή φακέλου…|Επαναφορά προεπιλογής|Αφαίρεση θέσης|Αρχείο…|Φάκελος…|Εκκαθάριση|Στιγμιότυπο (Shift+Win+S)|Αντιγραφή (Ctrl+C)|Επικόλληση (Ctrl+V)|Πίσω (Alt+←)|Μπροστά (Alt+→)|Αναίρεση (Ctrl+Z)"),
"tr": ("Çarkı aç|Ayarlar…|Tamamen çık|Kapat (kısayol yeniden başlatır)|Klavye|Klasörler|Windows komutları|Sık kullanılanlar|Ses|İnternet|Ayarlar|Programlar|Del|"
"Hızlı klavye komutları|Standart klavye|Ana ve Windows özel tuşları|Dizinler ve klasörler|Programlar ve uygulamalar|Çark ayarları|İnternet ve gezinme|Ses ayarları|Windows sistem komutları|Sık kullanılanlar ve hızlı erişim|"
"Tarayıcı seç|Google araması|Kayıtlı siteler|Ses düzeyi|Oynatma aygıtları|Belgeler|Resimler|Müzik|Videolar|Projeler|İndirilenler|Arşiv|Sistem|Tarayıcı|Düzenleyici|Oynatıcı|Hesap makinesi|Grafik|Posta|Oyunlar|Notlar|"
"Başlat|Görev Yön.|Ayarlar|Kilitle|Uyku|Yeniden başlat|Kapat|Çalıştır|Bilgisayar yeniden başlatılsın mı?|Bilgisayar kapatılsın mı?|Ekle|Ara|Google’da ara…|"
"Dosya / program seç…|Klasör seç…|Varsayılanı geri yükle|Yuvayı kaldır|Dosya…|Klasör…|Temizle|Ekran görüntüsü (Shift+Win+S)|Kopyala (Ctrl+C)|Yapıştır (Ctrl+V)|Geri (Alt+←)|İleri (Alt+→)|Geri al (Ctrl+Z)"),
"ru": ("Открыть колесо|Настройки…|Выйти полностью|Закрыть (горячая клавиша запустит снова)|Клавиатура|Папки|Команды Windows|Избранное|Звук|Интернет|Настройки|Программы|Del|"
"Быстрые команды клавиатуры|Стандартная клавиатура|Основные и специальные клавиши Windows|Каталоги и папки|Программы и приложения|Настройки колеса|Интернет и просмотр|Настройки звука|Системные команды Windows|Избранное и быстрый доступ|"
"Выбрать браузер|Поиск Google|Сохранённые сайты|Громкость|Устройства воспроизведения|Документы|Изображения|Музыка|Видео|Проекты|Загрузки|Архив|Система|Браузер|Редактор|Плеер|Калькулятор|Графика|Почта|Игры|Заметки|"
"Пуск|Диспетчер задач|Параметры|Блокировка|Спящий режим|Перезагрузка|Завершение работы|Выполнить|Перезагрузить компьютер?|Выключить компьютер?|Добавить|Найти|Поиск в Google…|"
"Выбрать файл / программу…|Выбрать папку…|Вернуть по умолчанию|Удалить слот|Файл…|Папка…|Очистить|Снимок экрана (Shift+Win+S)|Копировать (Ctrl+C)|Вставить (Ctrl+V)|Назад (Alt+←)|Вперёд (Alt+→)|Отменить (Ctrl+Z)"),
"uk": ("Відкрити колесо|Налаштування…|Вийти повністю|Закрити (гаряча клавіша запустить знову)|Клавіатура|Теки|Команди Windows|Обране|Звук|Інтернет|Налаштування|Програми|Del|"
"Швидкі команди клавіатури|Стандартна клавіатура|Основні та спеціальні клавіші Windows|Каталоги й теки|Програми та застосунки|Налаштування колеса|Інтернет і перегляд|Налаштування звуку|Системні команди Windows|Обране та швидкий доступ|"
"Вибрати браузер|Пошук Google|Збережені сайти|Гучність|Пристрої відтворення|Документи|Зображення|Музика|Відео|Проєкти|Завантаження|Архів|Система|Браузер|Редактор|Програвач|Калькулятор|Графіка|Пошта|Ігри|Нотатки|"
"Пуск|Диспетчер завдань|Параметри|Блокування|Сплячий режим|Перезавантаження|Вимкнення|Виконати|Перезавантажити комп’ютер?|Вимкнути комп’ютер?|Додати|Знайти|Пошук у Google…|"
"Вибрати файл / програму…|Вибрати теку…|Повернути типове|Видалити слот|Файл…|Тека…|Очистити|Знімок екрана (Shift+Win+S)|Копіювати (Ctrl+C)|Вставити (Ctrl+V)|Назад (Alt+←)|Вперед (Alt+→)|Скасувати (Ctrl+Z)"),
"sv": ("Öppna hjulet|Inställningar…|Avsluta helt|Stäng (snabbtangenten startar igen)|Tangentbord|Mappar|Windows-kommandon|Favoriter|Ljud|Internet|Inställningar|Program|Del|"
"Snabba tangentbordskommandon|Standardtangentbord|Huvud- och Windows-specialtangenter|Kataloger och mappar|Program och appar|Hjulinställningar|Internet och surfning|Ljudinställningar|Windows-systemkommandon|Favoriter och snabbåtkomst|"
"Välj webbläsare|Google-sökning|Sparade webbplatser|Volym|Uppspelningsenheter|Dokument|Bilder|Musik|Videor|Projekt|Hämtade filer|Arkiv|System|Webbläsare|Redigerare|Spelare|Kalkylator|Grafik|E-post|Spel|Anteckningar|"
"Start|Aktivitetshant.|Inställningar|Lås|Vänteläge|Starta om|Stäng av|Kör|Starta om datorn?|Stänga av datorn?|Lägg till|Sök|Sök på Google…|"
"Välj fil / program…|Välj mapp…|Återställ standard|Ta bort plats|Fil…|Mapp…|Rensa|Skärmbild (Skift+Win+S)|Kopiera (Ctrl+C)|Klistra in (Ctrl+V)|Bakåt (Alt+←)|Framåt (Alt+→)|Ångra (Ctrl+Z)"),
"hu": ("Kerék megnyitása|Beállítások…|Teljes kilépés|Bezárás (a gyorsbillentyű újraindítja)|Billentyűzet|Mappák|Windows-parancsok|Kedvencek|Hang|Internet|Beállítások|Programok|Del|"
"Gyors billentyűparancsok|Szabványos billentyűzet|Fő és speciális Windows-billentyűk|Könyvtárak és mappák|Programok és alkalmazások|Kerék beállításai|Internet és böngészés|Hangbeállítások|Windows rendszerparancsok|Kedvencek és gyors elérés|"
"Böngésző választása|Google-keresés|Mentett oldalak|Hangerő|Lejátszóeszközök|Dokumentumok|Képek|Zene|Videók|Projektek|Letöltések|Archívum|Rendszer|Böngésző|Szerkesztő|Lejátszó|Számológép|Grafika|Levelezés|Játékok|Jegyzetek|"
"Start|Feladatkezelő|Beállítások|Zárolás|Alvó mód|Újraindítás|Leállítás|Futtatás|Újraindítja a számítógépet?|Leállítja a számítógépet?|Hozzáadás|Keresés|Keresés a Google-ben…|"
"Fájl / program kiválasztása…|Mappa kiválasztása…|Alapérték visszaállítása|Hely eltávolítása|Fájl…|Mappa…|Törlés|Képernyőkép (Shift+Win+S)|Másolás (Ctrl+C)|Beillesztés (Ctrl+V)|Vissza (Alt+←)|Előre (Alt+→)|Visszavonás (Ctrl+Z)"),
"ja": ("ホイールを開く|設定…|完全に終了|閉じる（ホットキーで再起動）|キーボード|フォルダー|Windowsコマンド|お気に入り|サウンド|インターネット|設定|プログラム|Delete|"
"クイックキー操作|標準キーボード|主要キーとWindows特殊キー|ディレクトリとフォルダー|プログラムとアプリ|ホイール設定|インターネットとブラウズ|サウンド設定|Windowsシステムコマンド|お気に入りとクイックアクセス|"
"ブラウザーを選択|Google検索|保存したサイト|音量|再生デバイス|ドキュメント|ピクチャ|ミュージック|ビデオ|プロジェクト|ダウンロード|アーカイブ|システム|ブラウザー|エディター|プレーヤー|電卓|グラフィックス|メール|ゲーム|メモ|"
"スタート|タスク管理|設定|ロック|スリープ|再起動|シャットダウン|ファイル名を指定して実行|コンピューターを再起動しますか？|コンピューターをシャットダウンしますか？|追加|検索|Googleで検索…|"
"ファイル／プログラムを選択…|フォルダーを選択…|既定に戻す|スロットを削除|ファイル…|フォルダー…|クリア|スクリーンショット (Shift+Win+S)|コピー (Ctrl+C)|貼り付け (Ctrl+V)|戻る (Alt+←)|進む (Alt+→)|元に戻す (Ctrl+Z)"),
"zh": ("打开轮盘|设置…|完全退出|关闭（热键可重新启动）|键盘|文件夹|Windows 命令|收藏夹|声音|互联网|设置|程序|Delete|"
"快捷键命令|标准键盘|主要键和 Windows 特殊键|目录和文件夹|程序和应用|轮盘设置|互联网和浏览|声音设置|Windows 系统命令|收藏夹和快速访问|"
"选择浏览器|Google 搜索|已保存的网站|音量|播放设备|文档|图片|音乐|视频|项目|下载|存档|系统|浏览器|编辑器|播放器|计算器|图形|邮件|游戏|笔记|"
"开始|任务管理器|设置|锁定|睡眠|重新启动|关机|运行|要重新启动计算机吗？|要关闭计算机吗？|添加|搜索|在 Google 中搜索…|"
"选择文件/程序…|选择文件夹…|恢复默认|移除槽位|文件…|文件夹…|清除|截图 (Shift+Win+S)|复制 (Ctrl+C)|粘贴 (Ctrl+V)|后退 (Alt+←)|前进 (Alt+→)|撤销 (Ctrl+Z)"),
"ko": ("휠 열기|설정…|완전히 종료|닫기(단축키로 다시 시작)|키보드|폴더|Windows 명령|즐겨찾기|소리|인터넷|설정|프로그램|Delete|"
"빠른 키보드 명령|표준 키보드|주요 키 및 Windows 특수 키|디렉터리 및 폴더|프로그램 및 앱|휠 설정|인터넷 및 브라우징|소리 설정|Windows 시스템 명령|즐겨찾기 및 빠른 실행|"
"브라우저 선택|Google 검색|저장된 사이트|볼륨|재생 장치|문서|사진|음악|동영상|프로젝트|다운로드|보관함|시스템|브라우저|편집기|플레이어|계산기|그래픽|메일|게임|메모|"
"시작|작업 관리자|설정|잠금|절전|다시 시작|시스템 종료|실행|컴퓨터를 다시 시작할까요?|컴퓨터를 종료할까요?|추가|검색|Google 검색…|"
"파일/프로그램 선택…|폴더 선택…|기본값 복원|슬롯 제거|파일…|폴더…|지우기|스크린샷 (Shift+Win+S)|복사 (Ctrl+C)|붙여넣기 (Ctrl+V)|뒤로 (Alt+←)|앞으로 (Alt+→)|실행 취소 (Ctrl+Z)"),
}
NAMES = {"de": "Deutsch", "fr": "Français", "es": "Español", "it": "Italiano", "pt": "Português", "nl": "Nederlands", "pl": "Polski",
         "cs": "Čeština", "ro": "Română", "el": "Ελληνικά", "tr": "Türkçe", "ru": "Русский", "uk": "Українська", "sv": "Svenska",
         "hu": "Magyar", "ja": "日本語", "zh": "简体中文", "ko": "한국어"}

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "app" / "lang"
    for code, blob in T.items():
        vals = blob.split("|")
        assert len(vals) == len(KEYS), (code, len(vals), len(KEYS))
        d = dict(zip(KEYS, vals))
        d["language.name"] = NAMES[code]
        (out / f"lang_{code}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ok", len(T))
