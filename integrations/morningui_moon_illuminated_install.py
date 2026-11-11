#!/usr/bin/env python3
"""MorningUI moon: install or refresh two illuminated-only realistic GPU textures."""
from pathlib import Path
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import ast, base64, hashlib, json, math, os, shutil, subprocess, sys, time

H = Path.home()
ROOT = H / 'morning-tv-ui'
LAB = H / '.local/share/morningui-illuminated-moon'
PYTHON = ROOT / '.venv3/bin/python'
V5 = ROOT / 'ui/weather_gpu_v26_data/v5w_release/V5WCard.qml'
DATE = ROOT / 'ui/weather_gpu_v26_data/v41_release/V41DateCardScene.qml'
ASSETS = ROOT / 'ui/weather_gpu_v26_data/v5w_release/assets'
PNGS = [ASSETS / 'moon_phase_current.png', ASSETS / 'moon_date_v5x.png']
SERV = H / '.config/systemd/user/morningui-illuminated-moon.service'
TIMER = H / '.config/systemd/user/morningui-illuminated-moon.timer'
MANIFEST = H / '.cache/morningui_illuminated_moon_backup.json'
TEXTURE_B85 = '''|JeWF01!$>Nk#wx0RR9200961|JwjV00;&K2L=TQ2L}fU2?z=d6%Gsw3k(?&6Au+08z3JZ8yy`XB`_%=BP}Ey9V$60Eip4T
HZ~wAJ3l%!J}@;lGymHFLjeg12@DGi7!D2?Ga?-#Gcz+YGcz+YGcz+YGcz+YGcz+YGcz+YGcz+YGcz+YGcz+YGcz+YGcz+Y
Gcz+YGc*6d01*fPZ~$-v0TBQK5di}c0sq7R8~^|U0s{d70000000000000C91_uEG0{{sB!~i%D00IF60t5sD1_cBI00000
0RjU61Q7)x1`;tr6CzPz2XTQEBQipfu@zEcp}{3H;qY>T(f`B%7y$tR0RaI30000000000000310s{p9!~h);0RaI400RI6
0000000000009vK5+N}IK~ewO01N{G00I#M5dc2`q3gSo)hDV#wEaHsRJ=<|8(FSy9N}Vx3o-f%Jft#Ov~(YVTAkM<y6ya0
avl5#fR=1~{#E|<&#%e+ZgKrsI&Z?h1k*qg*|qC|lJ}D{Xa4|Iz^r-N-;9Fg(fD4~f?8-=Tq7H1-Ew}UQK_QYXfo|SkEImo
M7F7)+O0r!FNfR}ti#O?m2Yh>H+xAMET3VLKecPhj~K4?pM!Tu&e|p4j#qO9&J~BI7;Ju^R;Pc~Zz}Io(l7LDwzbqPCAOS?
Nf#L&qp=?1y2~%eJ1`AN>XX!`s83XrUI+MldBv~xshrvANZ5OVGR{X;LEQWF6^^@+zIfH=q1b5LGjIGmhwT+4Vds%oncv-?
zwKNtwbnrrHlptFtm=i2DJ6pE+a`m6TSzw(GzR)*5wH$bNJ4&n>eSNfNS+9rG8Y*j72j^gofsBPCFPF*xoi${MgZHlty;0i
PKWGw3?cD6K3(#1bCJF~3X%MG9w=lE>e%uy+kby*fE`aywb!iv#j9CEcNaHOFw5=;-A}l!ON$hz82mrE;pUR^!QS&q&-<A3
!|dbJ`i9>s>(5%}*Eofdis-`?C#Xq(0`Qt~4x#po?q$;;Z@k9FR{lVLbJ%;D$6aH5^Q*Gn!KGO2Ear~d(k1@@Z3jW<2l%cQ
y5Rf$UOf;CSfd$41)a9f%Cq$RBK|sc3Cm7_eAz*qf$55DS~fN}HwPJ0otSNk3PT0rL=qMrB!mD4Ml<W4)c~5dvuh5ZY?UQ$
Knnl>2u(SwNiJtgc^XKjXI92kj1iw&MRtjA;JgQu#EMkN4A=wQdK!_;HV&?@ZOm{+#N?WjY3*V%x|ri&$(KX8<vl?i#agjM
d`RF!!&iUAbo3`lxNHD7@EHD6{U@>dS8hAsu3ht=5E|;h%_mKtSk*1;Er;IB{GgtSI+i}bWY%rNCa*0v!YwMo3mY%PAC*Qw
RzBqKTran1kl5VAr$r;WhLGfuf^sV~qnf<0c1-fQF5L;=Z%SaGZ3BWxQb;=!+Nz=LiMW>KLbkwpw*LPBI>|bJ4Wo%xXw1sk
2;NdhQ<{n^cX9rqG}3K59l$#u_^n9IV(Q?>WY5e9EsXo^QWe75gwg6|8K1<6k1Da>=~Xd0dyz3@wj7e<AZNBle}0vcMZ`~e
Yif=O49r)=#^7V6Fj9Rg^50*MZ3|aZBo{Fl*B}7ipCjBKYSs1ZZu(Ig{*f+&uHI>rH#1wvR6p~tX8MZn&Di7A%9{Kz(tumN
UR(e^<}CN<TlLs}wa@Zj(|kptrrWi}!lY@;<n;qPS1ojb^*q2+1RiYUb=sv#-KBTu@V@A`DbC<+wIEa$vSd2o61!)i@3*$p
Qw5De>e5dY6&X$gFD?TgY*B|#ZKsJX7XIqhR$`|a8^%BH)})8sK=*o#lgGI&<`Ir{1JvWCX@?1{=aWkf<J&Ym#Ip%<RQ~`_
>MGJ*Z*|~Y#WZZKFd0G=kiOgZ_pM;jlkpsa`Z-FrRl#HjA*k_QN%e-gXT&;W+IW^mEHJV<5JAUH`qpzA-66H%`^zm_DWzEa
7@L^5Zll<B%{Qq;h;PNM8Vj2^xQ5qx5^n<Q8;$<}3H@?DwZF&KdS||O*zF=Aq-Yiv1|C)xsUseT#Bt1X`qpo{XQYQu)XlyO
P0C2g#>e%e4!Yd)%Wl^M4xVB<?t4&$X?j{;BYog!iylBa{d!etkj^ayZHJ0alQ;vWJ&hW0HS}WICGf(lCP-`obL&(TfZXa@
!c7RaWkfzhoCe0mpHXg>Tg9tdUO$H$BC>L^&*JtXwd%9%?^n`%9v=%IF5tg94qfrn9mmdyP<2Uw-HJXi2XC!ukuljcfnN*&
-0hK(PNS_Z^`W$6lg%7{R9xc(oag6QzgmNI{wcW+;a$Wf$pf4m5I@aVlcF`N1i#?DTFga{8aHLY>ch;Z^#ZB%UxoZdV9?DQ
qLUj&in#5B0;yL}svj2H8Hu^aUT^bSWjNv6WxKNb_fX0PMtgtuv0IMXX?q)nSRN#Zx!sP(>DGjId8tj{co<O-J#p03P@PKd
>TNn;vIyr^+ot~jD%AANX{Kv0V`vh1SxOLj$lT{_Z$&XBuvEB;IgCo#ZhmJQk?3e98ojg^(V`;ljNo*nB69FV%`v!HV~qnH
xpwuZMm?ZHA-K2)m6$0|I*t0`s-qh2pO{n#j7kqWl~IQI`&AVqw1AC4O0MVEr8nS-v^s0q#{@D<;v>c~N55*zRg3sx)Hre(
^SO#CBO|8kN9|NB!yznLgOQ!i`T5q^6Q$oZnx3RaLk0&J&fEIYV^CsVmE<7C=o=fH9Pfkus6ur8TH)mg7b_m;oMaGt;-jv&
aao&ylDS@X8>r9F)u`d@?EDT#aOyV<>z+~QMFp%ZBVZ$xczqYsH6v(*QJzsRGh;bH-_oREa}vvC_DKqYz!eMB=hRXWTm3OK
;Uv+&h7kzQE^^+Osvz1vuRfrYL3Se%st#UZfG~RdQ)UTtEzOJ&z$IA;oyU}QEIn$|hWdDsriuwc2&@2O)QoSRtqC6By-H0>
fpmFdB2WTBaEE?gQdFFLxlKJ!VqZ*MSvH@lI)GX^2^j0lJ*q+4KN3}lLU|mVC>yx?RGjP@D|?jj;w>0rq-O^m^FoapM>lsb
9DJ%=;{))F?eytN9eFz3SbhE=niUSbzn`@cI%wDJEJ<x5nHEOJKQQU?>s2uJ8(wfD@XF_K0me_xf+jLz3>rmQSmZ`JpO>XU
tT)m|?JFq+W0M`KBQ*marKhsD<T+>g{{Wg`M(ng_x4K)1=JQH93=NHke4k-Wx-$)<(V5-}n77@wRY#{`^sKby#FxLqwEOK!
LxzeMko>~!{qavfMfj;c59?kX&EAUgW5pgkAfBv05dAQIhPwC9?azv}+ZP2($LEesr0zYx=D4~#SlW(K(jX;Cc7B){JNs0K
^+(d~FB&*mUEP5#9!C8!pMP3?hgY<F8wqTk<5M=pvQ7p;`r{Q6E68V1(W5KKpy7{k?V4bA;n^+iwFw>6D>8-Yl25nRs-kXS
7dIo$>ljRhBc?jmT5^ih#khBJRI1}Gu>-Y9i6awEs15-9*`zmXl`$kiM}$2#B>I|@NckQ7QlqH~qqn6=B(#}+z#d`-0m~k~
-(1ucPsVL=EqGQPIT(qrqzXYh_-nf#spS=}CehW%qjb$i<4M%*ukBkCTgV+f2_28I8&`g&$0>33CkpFYe!ZpJ-bSHdxJ>MF
Rl9@oJ6E2}c9%uVYK*fiXmUXXIj~6e6cv4`X;%=>gpGoR#&evG#<i^2JjW|(sU*`LbA^qV;e!L$J;pt2BvR-vtjCz7Lo7oM
h;|3mdw$gF!Ma}wh_3nE5<vw|Hg=;<Cck7zkVvIe^5Clt$*E~&=P6^1a}mCFIrlYU(#D*qWq}6kg3Z+X3PTI$bXiy~{{V$f
{{Zn)5Vn3@-wT3pI%0y>TegDL*@{O5Yx%k;9rOFtpEz;H6E_rbB-e_^?6Hpu+#lo}{--9p@iI8|bsMd+neY!9zYO0st<$&g
%ZALD-@$L^1N#x_@~m~vx6NOc_d(VfVVX8cIZ8>KsRyA4-`2Tfrn%qECDRo#$KomFDa(#w-!+ovx?ERrLX$*LBV;O^l|IIi
^v2FFvoi&Sk=*1-u>EmDH@A?hra4|hLgS`MKea`?vle3;E*)QR4n}@;AU9J2d0)+s$fL_hD3NXmD9IYAY>W}iPj7mYHqqyr
NutXWlEmW`Au~?=iwc8;$>mYkKli-_QG8M3er0|hv6Htg+bP+7Q$DA^>FZs8A3wJ~s-&*0Gf-lpns8qq-SEo`OOW?EV;$n^
(Pybl_VrV-_N;ZzwJPYb)NOUhBGk0o;P8?Gc+N-3m#Uwga<R8*r?`qh{QSU=F+y?k6cH<^29KDISHQu}Mm?&<uJCH0q|%b5
6amSMZcfx<Fgk!)qX?yWhfp>-sTIq7^WhAkiG7)l<Mj2VJgWF+VoA?l)gchZ+_F5pvB&s}vB1FYb5d3ObMaCec;?dhVqSS0
D=qlwzR~)h>gYRq*G_o;vwBlZOEF?eCvr`6lN{KkGf-lr^+ax!tZF(X;JVXp<+hulD0X4!M?yYzn>5O^_<!R3L@YY(p<c#o
Wy+s&hjH{jO2y%+(sQQj{2{6*iD9eS_@{pW&Eb-N@oZLnY1nHOgo_uHGln69Ci(p{>p>qJ=%^tukiZ^OAje+6DzRx~lWAIe
v+6pXjif;H5hUt_`(rt$2BTWv#hw(>)sszIjZ))$v}41JpLT7?`3ih$)l<bE5VhVZ4Gqk~-pHM;E%K;+IgeKQ{*}^mj9!sb
y=j&zEYu(W*#'''


def lunar_calculation(moment):
    sys.path.insert(0, str(H / 'morningui_moon_phase_review/vendor'))
    import astronomy
    local = moment.astimezone(timezone.utc)
    t = astronomy.Time.Make(local.year, local.month, local.day, local.hour,
                            local.minute, local.second + local.microsecond / 1e6)
    phase = (astronomy.MoonPhase(t) % 360.0) / 360.0
    moon = astronomy.GeoVector(astronomy.Body.Moon, t, False)
    sun = astronomy.GeoVector(astronomy.Body.Sun, t, False)
    observer = astronomy.Observer(40.99165, -82.68168, 330.0)
    eye = astronomy.ObserverVector(t, observer, False)
    a = (sun.x-moon.x, sun.y-moon.y, sun.z-moon.z)
    b = (eye.x-moon.x, eye.y-moon.y, eye.z-moon.z)
    cosine = sum(x*y for x,y in zip(a,b)) / (
        math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b)))
    illum = (1.0 + max(-1.0, min(1.0, cosine))) / 2.0
    return phase, max(0.0, min(1.0, illum))


def refresh(check_only=False):
    from PySide6.QtCore import QPointF, QRectF
    from PySide6.QtGui import QImage, QPainter, QPainterPath
    tz = ZoneInfo('America/New_York')
    reference = datetime(2026, 11, 10, 19, 51, tzinfo=tz)
    phase_ref, light_ref = lunar_calculation(reference)
    if not (.025 < light_ref < .033 and 0 < phase_ref < .25):
        raise RuntimeError('STOP: Nov 10 astronomical comparison failed')
    print(f'VERIFIED Nov 10 7:51pm illumination: {light_ref*100:.3f}% waxing', flush=True)
    if check_only: return
    now = datetime.now(tz)
    phase, illumination = lunar_calculation(now)
    tex = QImage(str(LAB / 'texture.jpg'))
    if tex.isNull(): raise RuntimeError('Cannot read realistic lunar photo texture')
    size, radius = 256, 127.0
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)  # Transparent everywhere, including unilluminated Moon.
    if illumination > .00001:
        terminator = 1.0 - 2.0 * illumination
        waxing = phase < .5
        path = QPainterPath()
        for n in range(257):
            y = -radius + 2 * radius * n/256
            extent = math.sqrt(max(0.0, radius**2-y**2))
            x = terminator*extent if waxing else -extent
            point = QPointF(128+x, 128+y)
            if n == 0: path.moveTo(point)
            else: path.lineTo(point)
        for n in range(256, -1, -1):
            y = -radius + 2 * radius * n/256
            extent = math.sqrt(max(0.0, radius**2-y**2))
            x = extent if waxing else -terminator*extent
            path.lineTo(QPointF(128+x, 128+y))
        path.closeSubpath()
        circle = QPainterPath()
        circle.addEllipse(QPointF(128,128),radius,radius)
        p = QPainter(img)
        try:
            p.setRenderHint(QPainter.RenderHint.Antialiasing,True)
            p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,True)
            p.setClipPath(circle.intersected(path))
            p.drawImage(QRectF(0,0,256,256),tex,QRectF(3,3,tex.width()-6,tex.height()-6))
        finally: p.end()
    staged=[]
    try:
        for dest in PNGS:
            if not dest.is_file(): raise RuntimeError(f'Missing expected asset: {dest}')
            tmp = dest.with_name(dest.name+'.tmp.png')
            if not img.save(str(tmp),'PNG'): raise RuntimeError(f'Could not write {tmp}')
            staged.append((tmp,dest))
        for tmp,dest in staged: os.replace(tmp,dest)
    finally:
        for tmp,_ in staged: tmp.unlink(missing_ok=True)
    print(f'UPDATED moon images: {illumination*100:.3f}% {"waxing" if phase<.5 else "waning"}; unlit portion transparent',flush=True)


def change(text,old,new):
    if text.count(old)!=1: raise RuntimeError('STOP: QML moon anchor is not unique; no changes')
    return text.replace(old,new,1)


def install():
    paths = [V5, DATE] + PNGS
    if not all(p.is_file() for p in paths):
        raise SystemExit('STOP: Missing one of four approved live weather files')
    if MANIFEST.exists() or SERV.exists() or TIMER.exists():
        raise SystemExit('STOP: Installation already present; nothing overwritten')
    hashes={
        V5:'1e94dfdabd0be7d4a63381944fab7e1baeac32c333c0ed21c7bca601021e7a97',
        DATE:'23e09f8749992cdcf479d6f1db52f1a5759fd61f5488550f59d6f7d68596e1ae'}
    for path,expected in hashes.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise SystemExit(f'STOP: {path.name} differs from reviewed production; nothing changed')
    v=change(V5.read_text(),'    property string phaseMode: phase\n',
'''    property string phaseMode: phase
    // MORNINGUI_MOON_ONLY_V1: update Moon asset without changing other animations.
    property int moonRevision: 0
    Timer {
        interval: 600000
        repeat: true
        running: root.visible
        onTriggered: root.moonRevision += 1
    }
''')
    v=change(v,'''                source: Qt.resolvedUrl(root.nighttime
                    ? "assets/moon_phase_current.png" : "assets/sun_glow.png")''',
'''                source: root.nighttime
                    ? Qt.resolvedUrl("assets/moon_phase_current.png?rev=" + root.moonRevision)
                    : Qt.resolvedUrl("assets/sun_glow.png")''')
    d=change(DATE.read_text(), '    readonly property string weatherPhase: info.phase || "day"\n',
'''    readonly property string weatherPhase: info.phase || "day"
    // MORNINGUI_MOON_ONLY_V1: update the current-hour Moon image only.
    property int moonRevision: 0
    Timer {
        interval: 600000
        repeat: true
        running: root.visible
        onTriggered: root.moonRevision += 1
    }
''')
    d=change(d,'''        source: Qt.resolvedUrl(
            "../v5w_release/assets/moon_date_v5x.png"
        )''',
'''        source: Qt.resolvedUrl(
            "../v5w_release/assets/moon_date_v5x.png?rev=" + root.moonRevision
        )''')
    image=base64.b85decode(''.join(TEXTURE_B85.split()))
    if image[:3]!=b'\xff\xd8\xff': raise SystemExit('STOP: Image decode failed')
    subprocess.run(['systemctl','--user','is-active','--quiet','morningui-remote.service'],check=True)
    # Preflight dependency already installed for the approved 25-phase preview.
    dep='import sys;sys.path.insert(0,%r);import astronomy;from PySide6.QtGui import QPainter' % str(H/'morningui_moon_phase_review/vendor')
    subprocess.run([str(PYTHON),'-c',dep],check=True,timeout=15)
    print('PASS: Exact QML source hashes, unique anchors, astronomy engine, running UI')
    backup=H/('.cache/morningui_moon_before_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True)
    saved={}
    for i,path in enumerate(paths):
        dest=backup/(str(i)+'_'+path.name)
        shutil.copy2(path,dest);saved[str(path)]=str(dest)
    MANIFEST.parent.mkdir(parents=True,exist_ok=True)
    MANIFEST.write_text(json.dumps(saved,indent=2))
    try:
        LAB.mkdir(parents=True,exist_ok=True)
        (LAB/'texture.jpg').write_bytes(image)
        shutil.copy2(Path(__file__),LAB/'moon.py')
        # Verify lunar percentage before altering weather artwork.
        subprocess.run([str(PYTHON),str(LAB/'moon.py'),'check'],check=True,timeout=30)
        subprocess.run([str(PYTHON),str(LAB/'moon.py'),'refresh'],check=True,timeout=30)
        for path,updated in ((V5,v),(DATE,d)):
            tmp=path.with_name(path.name+'.moon.new')
            tmp.write_text(updated);shutil.copymode(path,tmp);os.replace(tmp,path)
        SERV.parent.mkdir(parents=True,exist_ok=True)
        SERV.write_text('[Unit]\nDescription=Realistic illuminated-only lunar texture for MorningUI\n[Service]\nType=oneshot\nExecStart='+str(PYTHON)+' '+str(LAB/'moon.py')+' refresh\n')
        TIMER.write_text('[Unit]\nDescription=Refresh lunar PNGs every 15 minutes\n[Timer]\nOnCalendar=*:0/15\nAccuracySec=30s\nPersistent=true\nUnit='+SERV.name+'\n[Install]\nWantedBy=timers.target\n')
        subprocess.run(['systemctl','--user','daemon-reload'],check=True)
        subprocess.run(['systemctl','--user','enable','--now',TIMER.name],check=True)
        subprocess.run(['systemctl','--user','restart','morningui-remote.service'],check=True,timeout=45)
        time.sleep(3)
        subprocess.run(['systemctl','--user','is-active','--quiet','morningui-remote.service'],check=True)
    except Exception as e:
        print('INSTALL ERROR:',e,'— restoring sources and original Moon images')
        subprocess.run(['systemctl','--user','disable','--now',TIMER.name],check=False,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        SERV.unlink(missing_ok=True);TIMER.unlink(missing_ok=True)
        subprocess.run(['systemctl','--user','daemon-reload'],check=False)
        for path,backupfile in saved.items():shutil.copy2(backupfile,path)
        subprocess.run(['systemctl','--user','restart','morningui-remote.service'],check=False)
        MANIFEST.unlink(missing_ok=True)
        raise SystemExit('INSTALL ROLLED BACK')
    audit=H/'morningui_real_weather_v5_preview/V5_TROUBLESHOOTING_AUDIT.md'
    if audit.is_file():
        with audit.open('a') as f:
            f.write('\n## Illuminated-only Moon V1 — '+str(datetime.now())+'\n'
                    '- User-approved realistic lunar texture, transparent unlit portion.\n'
                    '- Astronomical topocentric illumination and waxing/waning orientation.\n'
                    '- Two Moon PNGs regenerated every 15 minutes. Only Moon QML URLs/timers edited.\n'
                    '- Preserved all other weather rendering, sizes, colors and UI components.\n'
                    '- Backups: '+str(backup)+'\n')
    print('=== INSTALLED ILLUMINATED-ONLY REALISTIC MOON ===')
    print('Moon timer:', subprocess.run(['systemctl','--user','is-active',TIMER.name],capture_output=True,text=True).stdout.strip())
    print('MorningUI:',subprocess.run(['systemctl','--user','is-active','morningui-remote.service'],capture_output=True,text=True).stdout.strip())
    print('Rollback manifest:',MANIFEST)

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1] in ('refresh','check'):
        refresh(check_only=sys.argv[1]=='check')
    else:
        install()
