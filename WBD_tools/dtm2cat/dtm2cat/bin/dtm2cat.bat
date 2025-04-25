REM onderstaande invoer is in ieder geval nodig
set logfile=dtm2cat.log
set wl_prn=waterloop.csv
set pvwl_prn=peilvakken.csv
set peilvak=peilvakken.asc
set waterloop=waterlopen_verrasterd_dtm2catId.asc
set maaiveld=hoogtekaart_interp.asc
set specafv=out\specafv_clusters_BD.asc
set dijk=out\dijk_clusters_BD.asc
set tertiair=out\tertiair_clusters_BD.asc
set afwatering=out\afwatering_clusters_BD.asc
set lateral=out\waterloop_clusters_BD.csv

REM Deze invoer is optioneel
REM set specafv=specafv.asc
REM set dijk=dijk.asc
REM set tertiair=tertiair.asc

set prog_exe=dtm2cat.exe
set succes_hib=succes.hib

REM Verwijder de log-file en de succes-file als deze al bestaan

if exist %logfile% del %logfile%
if exist %succes_hib% del %succes_hib%

REM Geef de lijst met argumenten weer, zowel naar het scherm als naar de logfile

@echo Programma %exe_dir%\%prog_exe% wordt aangeroepen met de argumenten:
@echo %logfile%
@echo %wl_prn%
@echo %waterloop%
@echo %pvwl_prn%
@echo %peilvak%
@echo %maaiveld%
@echo %specafv%
@echo %dijk%
@echo %tertiair%
@echo %afwatering%
@echo %lateral%
@echo ..

@echo %date% %time%    >> %logfile%
@echo ..               >> %logfile%
@echo Programma %exe_dir%\%prog_exe% wordt aangeroepen met de argumenten:    >> %logfile%
@echo %logfile%        >> %logfile%
@echo %wl_prn%         >> %logfile%
@echo %waterloop%      >> %logfile%
@echo %wlinpv%         >> %logfile%
@echo %peilvak%        >> %logfile%
@echo %maaiveld%       >> %logfile%
@echo %specafv%        >> %logfile%
@echo %dijk%           >> %logfile%
@echo %tertiair%       >> %logfile%
@echo %afwatering%     >> %logfile%
@echo %lateral%        >> %logfile%
@echo ..               >> %logfile%

REM Draai het programma %prog_exe%

%prog_exe% %logfile% %wl_prn% %waterloop% %pvwl_prn% %peilvak% %maaiveld% %specafv% %dijk% %tertiair% %afwatering% %lateral% 

if exist %succes_hib% goto eind2

REM Programma niet correct uitgevoerd

@echo Het programma %prog_exe% is niet succesvol uitgevoerd
@echo Raadpleeg de log-file %logfile%
@echo ..  >> %logfile% 
@echo Het programma %prog_exe% is niet succesvol uitgevoerd  >> %logfile%

goto eind

:eind1

REM Arumentenlijst niet compleet

@echo De argumentenlijst voor deze batchfile is niet compleet
@echo Gebruik de 3 argumenten Project Model Scenario 
@echo ..  >> %logfile% 
@echo De argumentenlijst voor deze batchfile is niet compleet  >> %logfile% 
@echo Gebruik de 3 argumenten Project Model Scenario >> %logfile% 
@echo ..  >> %logfile% 
@echo Het programma %prog_exe% is niet succesvol uitgevoerd  >> %logfile%

goto eind

:eind2

REM succes

del %succes_hib%
@echo Het programma %prog_exe% is correct uitgevoerd
@echo Zie de log-file %logfile% voor details
@echo ..  >> %logfile% 
@echo Het programma %prog_exe% is correct uitgevoerd >>  %logfile%

:eind
pause