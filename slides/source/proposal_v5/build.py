# -*- coding: utf-8 -*-
"""TW01 Proposal v5: white-background research deck (23 main + 9 appendix).
Adds Deep Research, Article Summary, Agent design (architecture/flowchart/pseudocode).
No model or product changes; frozen sources only."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import zipfile
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.oxml.xmlchemy import OxmlElement
from pptx.util import Inches, Pt

VERSION='v5'
NAME='FMPA_Proposal_v5'
FONT='Microsoft JhengHei'
MONO='Consolas'
INK='222B33'; ACCENT='315A70'; MUTED='606B74'; LINE='CDD4DA'; LIGHT='F1F4F6'; WHITE='FFFFFF'
WARN='7A4A21'
WIDTH,HEIGHT=13.333333,7.5
MAIN_COUNT=23
SOURCES={
 'D1':'臺中市政府公有零售市場每日蔬果價格表，data.gov.tw資料集84539；https://data.gov.tw/dataset/84539 。使用既有2026-10-03快照，不重新下載。',
 'D2':'outputs/proposal_delivery/run3_20261004_01/stats_master.json: descriptive/splits/purge；2026-10-08本輪唯讀重核一致。',
 'E1':'outputs/evaluation/public/public_test_results.json: horizons.h=7 / h=14；SHA256 2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8。固定測試列，未重算模型輸出、未重訓。',
 'E2':'outputs/evaluation/public/public_test_results.json: by_crop；同一封存測試的分品項描述。',
 'M1':'docs/LABEL_CONTRACT.md；src/aiot_price/data/labels.py；docs/proposal_v5/PROPOSAL.md。h=7/14個日曆日；t為本次可信報價基準日；缺到期正價格者無標籤。',
 'M2':'src/aiot_price/models/store_adapter.py: ALPHA_EXPERIMENTAL=0.3；docs/STORE_DATA_PROTOCOL.md。A為乘法錨定；B為固定規則，不是學得的增益。',
 'M3':'outputs/training/training_results.json；models/releases/0.1.0/manifest.json；src/aiot_price/models/train.py。候選Ridge、RFRegressor、HGBRegressor、DummyMajority、HGBClassifier；12個數值特徵＋crop_id one-hot，無市場one-hot。',
 'S1':'outputs/proposal_delivery/run3_20261004_01/stats_master.json: purge.segments。成熟日=t+h+1；7天清除帶8日、14天15日。',
 'A1':'src/aiot_price/api/app.py: /forecast, /agent/query, /records；src/aiot_price/agent/tools.py: AgentTools（get_market_quote、post_forecast 兩工具）＋ToolCallLimiter＋parse_query；src/aiot_price/models/predict.py: ForecastEngine；prediction_records: private/predictions。依既有原型整理；save_record 尚未封裝為 AgentTool（/records 由 Web 另呼）。',
 'U1':'outputs/e2e/ui_ab_mobile_390x844.png，2026-10-03本機原型截圖。只裁出上方7天A/B結果區並明示裁切，未改內部數字、未偽造新查詢。',
 'P1':'docs/proposal_v5/PROPOSAL.md；docs/CONTRIBUTIONS.md；TASKS.md。使用者2026-10-04指示產品代理人整合與SERVER暫緩；2026-10-08指示Proposal v5第一階段（文件與簡報，不改產品程式）。',
 'R01':'陳泯宏（2024），《國產大宗蔬菜價格預測模型之比較》，臺灣大學統計碩士學位學程。DOI 10.6342/NTU202400875；https://tdr.lib.ntu.edu.tw/handle/123456789/92775 。沿用既有摘要全文查核，未讀全文。',
 'R02':'李岱鑫（2015），《高雄果菜運銷公司高麗菜批發價格預測之研究—蒐集私有資料的價值》，清華大學。https://etd.lib.nycu.edu.tw/cgi-bin/gs32/hugsweb.cgi?o=dnthucdr&s=id%3D%22GH02102077503%22.&searchmode=basic 。沿用書目與摘要查核；實際評估指標仍UNKNOWN。',
 'R04':'農委會×財政資訊中心（2018）農業大數據平台：電子發票農產品零售價格估計。農傳媒報導《從29億張電子發票撈蛛絲馬跡…》https://www.agriharvest.tw/archives/12897 ；報導全文實讀，平台未登入。',
 'R03':'林沂臻（2017），《應用希爾伯特-黃變換之菜價預測》，中山醫學大學碩士論文（NDLTD 105CSMU5585004）。沿用索引摘要查核；全文未取得。',
 'R07':'YuehChun（2025），NCHU-Data-Mining-Project：氣候×台灣蔬菜價格探勘，GitHub repo（2025-05更新）https://github.com/YuehChun/NCHU-Data-Mining-Project 。repo+README層級。',
 'R10':'農糧署（2026），115年度補助計畫公告：結合生成式AI與預測式機器學習於農產品產銷決策支援架構之先導研究（115農科-4.4.1-糧-02）https://www.afa.gov.tw/cht/index.php?act=download&ids=47334 。公告PDF全文實讀；公告非成果。',
 'R05':'flux6lab，白菜即時官方頁 https://cabbagelive.com/ 。沿用已讀產品文案：中長期趨勢預測／零售換算。未安裝實測，不把文案當成效果證據，未載明功能保持未知。',
 'R06':'鹿中創客，農產分析Google Play頁 https://play.google.com/store/apps/details?id=com.bvc_dev_team.androidapp&hl=zh-TW 。沿用已讀文案：輸入購買價、換算及當日行情比對；未安裝實測。',
 'H17':'同課程Team17，《蔬果價格預測：LightGBM的最佳採購指南》（2025），本機歷屆/AIoT_歷屆期末簡報/regular_ii/Team17_蔬果價格預測_LightGBM採購指南.pdf。2026-10-08本輪第一手逐頁影像閱讀11/15頁（第1–4、7–12、15頁）；第5、6、13、14頁主題依同批逐頁筆記補足。只依作者簡報，不是已獨立重現的研究結果。',
 'W1':'王鎬杰（2010），《近年颱風、豪雨後批發市場蔬菜交易價量變動分析》，農糧署《農政與農情》第219期；https://www.moa.gov.tw/ws.php?id=22086 。官網全文實讀（2026-10-04）；2004–2009全台批發週均價之歷史統計，非本案期間地區。',
 'N1':'公視新聞2025-08-13「豪雨、颱風導致菜價上漲 台北傳統市場1把蔥380元」https://news.pts.org.tw/article/765375 。官網原文實讀；早於本案資料期間（2025-10-04起），僅消費端歷史背景。',
 'G1':'docs/proposal_v5/DEEP_RESEARCH.md（五思維／三爭論／十問題，含證據與推理）；docs/proposal_v5/ARTICLE_SUMMARY_TABLE.md（八欄表10件＋來源層級）。',
 'AD1':'docs/proposal_v5/AGENT_DESIGN.md：架構五群組①–⑤、工具層CURRENT／PROPOSED對照（get_market_quote/post_forecast現況；save_record工具化屬Proposed）、安全約束11條、D1–D9流程圖（節點標狀態）、Algorithm 1（主講10步＋完整41行）與Pseudocode↔實作映射。',
 'C1':'會議錄音 10.txt:1710–1718、1890–1916（模型＋Domain Agent要求）；教授L4-1 https://app.notion.com/p/AIoT-DA-L4-1-Proposal-1-3ebc4752981180d8842fd7e253962c4e 。沿用已讀正文與逐字稿。',
 'DD1':'docs/proposal_v5/DESIGN_DELTA.md：v5與根目錄design.md之沿用／新增／待同步／未來分界；本輪不覆寫正式design.md。',
 'STYLE':'沿用v4簡潔白底風格（simple_v4），參考Team17第7–10頁資料與結果安排、GUARD總覽與局部說明、LSTM簡潔視覺、蜜蜂健康Related Work論述。不複製他組數據、圖片、成果或新功能。'
}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def color(v): return RGBColor.from_string(v)

def validate_table_geometry(rows,colwidths,heights,width,tol=0.06):
    """表格幾何不變量（REVIEW_R2 V4）：欄寬總和必須等於指定總寬。
    python-pptx 逐欄設絕對寬會覆蓋 add_table 的名目 width——總和不符即版面錯版，
    在生成期 fail-fast，不得等到渲染後才發現。"""
    ncols=len(rows[0]) if rows else 0
    if len(colwidths)!=ncols:
        raise ValueError(f'table geometry: {len(colwidths)} colwidths for {ncols} columns')
    if len(heights)!=len(rows):
        raise ValueError(f'table geometry: {len(heights)} heights for {len(rows)} rows')
    total=sum(colwidths)
    if abs(total-width)>tol:
        raise ValueError(f'table geometry: colwidths sum {total:.2f}in != width {width:.2f}in (page will render {total:.2f}in wide)')

def no_effects(shape):
    sp=shape._element.spPr
    for tag in ['a:effectLst','a:effectDag']:
        old=sp.find(qn(tag))
        if old is not None:sp.remove(old)
    sp.append(OxmlElement('a:effectLst'))
    style=shape._element.find(qn('p:style'))
    if style is not None:
        ref=style.find(qn('a:effectRef'))
        if ref is not None:ref.set('idx','0')

class Deck:
    def __init__(self,root,out,evidence):
        self.root,self.out,self.evidence=root,out,evidence
        self.prs=Presentation();self.prs.slide_width=Inches(WIDTH);self.prs.slide_height=Inches(HEIGHT)
        cp=self.prs.core_properties;cp.title='TW01 現場菜價7／14天預測與分析代理人';cp.subject='Proposal v5（Deep Research＋Agent設計＋初步成果）';cp.author='TW01 project'
        cp.created=cp.modified=datetime(2026,10,8)
        self.notes,self.layout=[],[]
        self.eval=json.loads((root/'outputs/evaluation/public/public_test_results.json').read_text(encoding='utf-8'))
        self.stats=json.loads((root/'outputs/proposal_delivery/run3_20261004_01/stats_master.json').read_text(encoding='utf-8'))
        assert sha(root/'outputs/evaluation/public/public_test_results.json')=='2d28acd2f2c3e5ce566b9095c6a85477db8faf858d9ce29e974caaedc25674b8','Frozen evaluation changed; inspect before authoring.'
        assert self.stats['descriptive']['h7|ALL']['nonflat']==1149
        assert self.stats['descriptive']['h14|ALL']['nonflat']==1773
        self.shot=root/'outputs/e2e/ui_ab_mobile_390x844.png'
        if not self.shot.is_file():raise FileNotFoundError('Required historical UI screenshot is missing.')

    def text(self,s,x,y,w,h,text,size=22,bold=False,tint=INK,align='left',linespace=1.16,font=FONT):
        box=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=box.text_frame
        tf.word_wrap=True;tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0;tf.vertical_anchor=MSO_ANCHOR.TOP
        for i,line in enumerate(str(text).split('\n')):
            p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.alignment={'left':PP_ALIGN.LEFT,'center':PP_ALIGN.CENTER,'right':PP_ALIGN.RIGHT}[align]
            p.line_spacing=linespace;p.space_after=Pt(2)
            r=p.add_run();r.text=line;r.font.name=font;r.font.size=Pt(size);r.font.bold=bold;r.font.color.rgb=color(tint)
            ea=OxmlElement('a:ea');ea.set('typeface',FONT);r._r.get_or_add_rPr().append(ea)
        self.layout.append({'page':len(self.prs.slides),'kind':'text','x':x,'y':y,'w':w,'h':h,'size':size,'text':str(text)})
        return box

    def line(self,s,x1,y1,x2,y2,tint=LINE,width=1,arrow=False,dash=False):
        obj=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,Inches(x1),Inches(y1),Inches(x2),Inches(y2));obj.line.color.rgb=color(tint);obj.line.width=Pt(width)
        if dash:obj.line.dash_style=MSO_LINE_DASH_STYLE.DASH
        no_effects(obj)
        if arrow:
            ln=obj.line._get_or_add_ln();end=OxmlElement('a:tailEnd');end.set('type','triangle');ln.append(end)
        return obj

    def box(self,s,x,y,w,h,fill=WHITE,stroke=LINE,dash=False):
        sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
        sh.fill.solid();sh.fill.fore_color.rgb=color(fill);sh.line.color.rgb=color(stroke);sh.line.width=Pt(1)
        if dash:sh.line.dash_style=MSO_LINE_DASH_STYLE.DASH
        no_effects(sh)
        return sh

    def page(self,title,section,footer):
        s=self.prs.slides.add_slide(self.prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=color(WHITE)
        self.text(s,.65,.30,11.85,.25,section,11,tint=ACCENT)
        self.text(s,.65,.72,12,.61,title,29,bold=True)
        self.line(s,.65,1.47,12.68,1.47)
        self.text(s,.65,7.02,11.6,.23,footer,10,tint=MUTED,linespace=1)
        self.text(s,12.02,7,.66,.27,str(len(self.prs.slides)),11,tint=MUTED,align='right')
        return s

    def takeaway(self,s,text,y=6.42):
        self.line(s,.65,y-.17,1.15,y-.17,tint=ACCENT,width=2)
        self.text(s,.65,y,12,.44,text,19,bold=True,tint=ACCENT)

    def points(self,s,items,x=.75,y=1.9,w=11.8,size=22,gap=1.18):
        for i,(head,body) in enumerate(items):
            yy=y+i*gap
            self.text(s,x,yy,.48,.43,f'{i+1:02d}',16,bold=True,tint=ACCENT)
            self.text(s,x+.68,yy,w-.68,.46,head,size,bold=True)
            self.text(s,x+.68,yy+.52,w-.68,.70,body,size-2,tint=MUTED)

    def table(self,s,x,y,width,colwidths,heights,rows,size=19,highlight=(),hsize=None):
        validate_table_geometry(rows,colwidths,heights,width)
        sh=s.shapes.add_table(len(rows),len(colwidths),Inches(x),Inches(y),Inches(width),Inches(sum(heights)));tbl=sh.table
        for i,w in enumerate(colwidths):tbl.columns[i].width=Inches(w)
        for i,h in enumerate(heights):tbl.rows[i].height=Inches(h)
        for ri,row in enumerate(rows):
            for ci,txt in enumerate(row):
                c=tbl.cell(ri,ci);c.text=str(txt);c.margin_left=c.margin_right=Inches(.08);c.margin_top=c.margin_bottom=Inches(.05);c.vertical_anchor=MSO_ANCHOR.MIDDLE
                c.fill.solid();c.fill.fore_color.rgb=color(LIGHT if ri==0 or ri in highlight else WHITE)
                pr=c._tc.get_or_add_tcPr()
                for edge in ['lnL','lnR','lnT','lnB']:
                    found=pr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}'+edge)
                    if found is not None:pr.remove(found)
                    ln=OxmlElement('a:'+edge);ln.set('w','6350');sol=OxmlElement('a:solidFill');cc=OxmlElement('a:srgbClr');cc.set('val',LINE if edge=='lnB' else WHITE);sol.append(cc);ln.append(sol);pr.append(ln)
                for p in c.text_frame.paragraphs:
                    p.space_after=Pt(1);p.line_spacing=1.08
                    for r in p.runs:
                        r.font.name=FONT;r.font.size=Pt((hsize or size) if ri==0 else size);r.font.color.rgb=color(ACCENT if ri==0 else INK);r.font.bold=ri==0
                        ea=OxmlElement('a:ea');ea.set('typeface',FONT);r._r.get_or_add_rPr().append(ea)
        self.layout.append({'page':len(self.prs.slides),'kind':'table','x':x,'y':y,'w':width,'h':sum(heights),'rows':rows})
        return sh

    def note(self,s,title,seconds,script,ids,extra=''):
        no=len(self.prs.slides);assert all(k in SOURCES for k in ids)
        role='主講' if no<=MAIN_COUNT else '附錄';src='\n'.join(f'[{k}] {SOURCES[k]}' for k in ids)
        text=f'{role} 第{no}頁｜{title}\n\n{script}\n\n補充／證據邊界\n{extra}\n\n來源\n{src}'
        if seconds:text+=f'\n\n預估講解時間：{seconds}秒（非實測配音長度）'
        s.notes_slide.notes_text_frame.text=text
        self.notes.append({'page':no,'kind':role,'title':title,'seconds':seconds,'script':script,'extra':extra,'source_ids':ids,'notes_text':text})

    # ---------- page builders ----------
    def p_cover(self):
        s=self.page('','Proposal v5：研究提案與初步成果','TW01｜Proposal v5｜版本日期 2026-10-08｜候選版，待獨立複審')
        self.line(s,.72,1.87,.72,5.77,tint=ACCENT,width=3)
        self.text(s,1.07,2.02,11.35,1.6,'現場菜價7／14天\n預測與分析代理人',36,bold=True)
        self.text(s,1.10,4.05,10.9,1.0,'今天看見的單品價格，如何連到一、兩週後的變化？\nAgent 選工具、模型算價、程式驗證、證據說明。',22,tint=MUTED)
        self.text(s,1.10,5.45,10.9,.60,'AIoT 應用與資料分析\n組員／組長、正式發表日期：待填',14,tint=MUTED)
        self.note(s,'封面',20,'我們的題目是現場菜價七天與十四天預測。這一版提案補上深度研究、文獻摘要表與代理人設計三種表示。分工原則一句話：代理人選工具、預測引擎算菜價、程式驗證、代理人依證據解釋。既有公開測試結果與負向發現全部保留，同店效果仍待驗證。',['P1','STYLE'],'本版為Proposal v5第一階段：研究與設計文件與簡報；不修改產品程式、不接線LLM後端。')

    def p_motivation(self):
        s=self.page('研究動機：今天的標價，還不足以回答未來','研究背景','[D1–D2] 臺中公開市場歷史資料；[W1] 農業部官方分析；[N1] 2025颱風新聞（背景）')
        self.text(s,.75,1.80,5.3,.4,'使用情境',18,bold=True,tint=ACCENT)
        self.text(s,.75,2.38,5.1,.66,'甘藍 32元／台斤',28,bold=True)
        self.text(s,.75,3.22,5.1,1.15,'消費者想知道：\n7天、14天後，會漲、平或跌？',20)
        self.text(s,.75,4.55,5.1,1.6,'價格確實會跳：官方分析顯示颱風後\n第1週批發均價平均上漲10–40%（2004–\n2009全台統計[W1]）；2025-08楊柳颱風\n後有一把蔥380元的零售情境[N1]。',15,tint=MUTED)
        self.text(s,6.58,1.78,5.8,.8,'歷史樣本中，超過±5%變動的配對比例\n（本案資料實算；歷史比例，非未來機率）',17,bold=True)
        D=self.stats['descriptive']
        for i,h in enumerate((7,14)):
            r=D[f'h{h}|ALL'];yy=2.98+i*1.20;bw=3.3*r['percent_exact']/20
            self.text(s,6.58,yy+.02,1.05,.4,f'{h}天',18)
            self.box(s,7.65,yy,bw,.36,ACCENT,ACCENT)
            self.text(s,7.65+bw+.17,yy-.04,1.2,.4,r['percent_display'],20,bold=True,tint=ACCENT)
            self.text(s,7.65,yy+.52,4,.3,f"{r['nonflat']:,}／{r['n']:,}筆歷史配對",12,tint=MUTED)
        self.text(s,6.58,5.48,5.9,.85,'同時：7天兩端完全同價者佔86.7%–92.8%\n——「多數不變、少數大變」是本問題的基本結構。',15,tint=MUTED)
        self.takeaway(s,'值得測短期方向；但市場均價不能直接當成同店真值。')
        self.note(s,'研究動機',30,'想像你站在蔬果行，看見甘藍一台斤三十二元。這個價格沒有回答一兩週後的變化。右圖用本案資料說明問題存在：七天有百分之十點五、十四天有百分之十六點六的歷史配對超過正負百分之五。官方對二〇〇四到二〇〇九年颱風的分析顯示災後第一週批發均價平均上漲一成到四成；二〇二五年八月楊柳颱風後也有一把蔥三百八十元的零售情境。但注意，七天完全同價的配對也接近九成——多數不變、少數大變，這決定了我們要用宏平均指標並與簡單基線比較。',['D1','D2','W1','N1'],'母體為市場×品項×起算日×期限之歷史配對（7天n=10,952、14天n=10,680），非獨立天數、非未來機率。[W1]為2004–2009全台批發週均價統計；[N1]早於本案資料期間，僅歷史背景。')

    def p_related(self):
        s=self.page('相關研究：預測、私人資料與課程前作','相關研究 1/3','[R01–R02] 論文摘要實讀；[R04] 報導全文；[H17] 原PDF第一手逐頁閱讀')
        self.table(s,.70,1.72,11.93,[2.95,3.55,3.23,2.20],[.40,1.02,1.02,1.02,1.02],[
            ['前作','已知做法','預測對象與期限','值得本案對照'],
            ['陳泯宏，2024','批發歷史價格；比較ARIMA、\nETS、TDNN、LSTM','批發價；期限未明示\n（摘要列RMSE/方向正確率）','模型選擇與\n方向評估'],
            ['李岱鑫，2015','公開資料＋中盤商私有紀錄；\n預測下一週批發價','高雄批發價；一週','新增私人資料\n是否有幫助'],
            ['大數據平台，2018','29億筆電子發票之零售\n價格估計＋颱風情境','零售估計（非店價）','零售層級的\n官方先例'],
            ['Team 17，2025\n同課程','LightGBM＋氣象特徵；\n六種冬季蔬菜各一模型','市場價格；未來五天\n（2024測試R²最高0.81）','最近的前作：\n資料、期限、應用']],size=16,hsize=16)
        self.takeaway(s,'前作多在批發／市場層級；消費者現場店價基準＋固定7/14天未見。',y=6.5)
        self.note(s,'相關研究：學術與課程前作',30,'學術上，陳泯宏比較多種批發價格預測模型；李岱鑫研究加入中盤商私有紀錄的價值；官方的大數據平台用二十九億筆電子發票估零售價。最接近的同課程前作是Team17：LightGBM加上氣象特徵，為六種冬季蔬菜各建一個模型，預測未來五天的市場價格，二〇二四測試集最好品項R平方零點八一。他們的輸入是市場與氣象歷史，不是使用者當下的店價；簡報也未見基線對照與氣象消融。本案把問題縮到消費者單店報價與固定七、十四天。',['R01','R02','R04','H17','P1'],'R01/R02依摘要；R04依報導（模型細節未公開）。H17本輪第一手閱讀11/15頁，其餘4頁依同批逐頁筆記；不跨資料比分數；未載明的功能不當「不存在」。')

    def p_products_gap(self):
        s=self.page('相關服務與研究缺口','相關研究 2/3','[R05–R06] 已查核官網／商店文案；未安裝實測，文案不是效果證據')
        self.table(s,.70,1.70,11.93,[3.10,4.55,4.28],[.40,.95,.95,.95],[
            ['服務／本案','已見功能或設計','證據界線'],
            ['白菜即時','菜價中長期趨勢預測、\n超市零售換算文案','模型、期限與效果\n未公開（UNKNOWN）'],
            ['農產分析','輸入購買價、單位換算、\n當日行情比對','止於當日；其他功能\n未載明（UNKNOWN）'],
            ['TW01 本案','今天店價＋選填上週價；\n估計t+7／t+14相對變化','公開市場已有測試；\n同店A／B效果尚未驗證']],size=17,hsize=17,highlight=(3,))
        gy=5.05
        for i,(x,head,body) in enumerate([(.75,'既有已做到','批發/市場預測（R01/R03/H17）、\n零售估計（R04）、當日比對（R06）、\n趨勢預測文案（R05）'),(3.85,'證據不足','未見：以使用者今天店價為基準、\n固定7/14日曆天方向、\n真店到期價驗證輸入增益'),(6.95,'本案另測','A現價錨定＋B上週店價差動量；\n凍結預測→到期同店實價\n配對驗證；附來源與狀態'),(10.05,'公平驗證','±5%門檻事前凍結；與不變價/\n動量同列；負向結果保留；\n不跨資料集排名')]):
            self.box(s,x,gy,2.95,1.25,WHITE,ACCENT if i==2 else LINE)
            self.text(s,x+.13,gy+.07,2.7,.3,head,14,bold=True,tint=ACCENT if i==2 else INK)
            self.text(s,x+.13,gy+.40,2.72,.82,body,10.5,tint=MUTED,linespace=1.08)
            if i<3:self.line(s,x+2.95,gy+.62,x+3.10,gy+.62,tint=ACCENT,width=1.6,arrow=True)
        self.takeaway(s,'差異靠任務與驗證說清楚，不靠「別人都沒有」來成立。',y=6.5)
        self.note(s,'相關服務與研究缺口',25,'產品端不能概括成「都只看今天」：白菜即時有趨勢預測與換算文案、農產分析能輸入自己買的價格比對當日行情。下方把缺口講清楚：既有工作做到哪裡、證據不足在哪裡、本案另測什麼、如何公平驗證。TW01的差異主張是任務定義與驗證協議，不是宣稱別人沒有的功能一定不存在。',['R05','R06','P1'],'產品未公開之欄位標UNKNOWN；「查核範圍內未見」限於REFERENCES所述檢索範圍，不是原創性宣稱。')

    def p_summary_main(self):
        s=self.page('文獻摘要表（教授八欄格式；主講精選5件）','相關研究 3/3','完整10件＋來源與查核層級見附錄A1–A3；UNKNOWN＝未載明，非「沒有」')
        self.table(s,.62,1.72,12.10,[.80,.76,1.56,1.60,1.68,1.64,2.03,2.03],[.42,.92,.92,.92,.92],[
            ['Ref.','Year','Problem','AI Method','Domain Knowledge','Dataset','Findings','Limitation'],
            ['R01','2024','大宗蔬菜批發價預測','ARIMA/ETS/TDNN/LSTM','批發價格結構與季節性','台灣批發2012–2022','甘藍前1期LSTM\n方向約6成','批發非店價；\n僅摘要'],
            ['R02','2015','私有資料對批發價預測的價值','時間序列；含/不含私有對照','供應鏈私有紀錄 vs 公開登記','高雄批發66週','含私有資料者\n誤差較低','批發脈絡；\n回測'],
            ['R06','2026','輸入購買價比對當日行情','換算比對（非預測）','台斤/公斤換算；當日行情','農糧署交易行情','證明現場輸入\n需求存在','止於當日\n比對'],
            ['H17','2025','蔬果價格預測與採購指南','LightGBM×6品項；氣象特徵','批發上/中/下價×氣象；防洩漏','批發+氣象\n2018–2024','2024測試R²\n0.41–0.81','市場層級；五天；\n未見基線/消融']],size=11,hsize=11.5)
        self.takeaway(s,'AI方法與領域知識並列閱讀；分數不跨資料集比較。',y=6.5)
        self.note(s,'文獻摘要表（精選）',25,'教授指定的八欄格式：問題、AI方法、領域知識、資料集、發現與限制。主講挑五件最關鍵的：兩篇學術、一個產品、一個課程前作。完整十件在附錄。閱讀方式是把AI方法與領域知識兩欄並列——菜價預測的文獻裡，領域知識（單位、層級、季節、災後結構）與演算法同等重要。各分數屬於各自的任務與資料，不能互比。',['G1','R01','R02','R06','H17'],'R05/R07/R10/W1與本案自列於附錄A1–A3；每件附來源與查核層級。')

    def p_rq(self):
        s=self.page('研究問題與三項貢獻','研究目標','[P1] RQ1–RQ3與C1–C3；已完成與待驗證分開')
        self.points(s,[('RQ1：固定期限的公開評估','7／14天方向預測與不變價、動量基線比較。　已有封存測試答案（含負向）'),('RQ2：A／B輸入增益','今天價（A）與選填上週同店價（B）有無幫助。　協議就緒；增益零證據（待驗證）'),('RQ3：低負擔與可追溯','兩欄輸入、附期限與來源的呈現能否兼顧。　原型就緒；人因未測')],y=1.85,gap=1.14,size=22)
        self.text(s,.75,5.50,11.8,.36,'三項貢獻',17,bold=True,tint=ACCENT)
        self.text(s,.75,5.96,11.8,.85,'C1（已驗證）固定期限＋強基線＋負向結果並列的臺中零售評估　│　C2（待驗證）A/B真店到期配對協議　│\nC3（初步）主張狀態可追溯的消費者端原型與Domain Agent設計',16.5)
        self.note(s,'研究問題與三項貢獻',25,'三個問題對應三項貢獻。第一問已有答案：模型勝全持平但未勝動量，這是誠實的發現。第二問是本提案明列的未來實驗：多一筆上週同店價是否有增益，目前零證據。第三問有原型但使用者研究未做。狀態標籤貫穿文件與介面。',['P1','E1'],'不把C1結果當原創性或泛化證實；C2之α=0.3未訓練；C3不含LLM後端（暫緩）。')

    def p_mindsets(self):
        s=self.page('深研究①：五個核心思維','Deep Research 1/3','[G1] 完整版：docs/proposal_v5/DEEP_RESEARCH.md（每項附證據與設計影響）')
        self.table(s,.70,1.72,11.93,[2.55,5.00,4.38],[.38,.84,.84,.84,.84,.84],[
            ['思維','白話解釋','對TW01設計的影響'],
            ['M1 價格可比性優先','不同店/規格/單位的價格不能直接相比；0是無價不是零元','B五重檢查（同店/品項/規格/單位/7±2天）；不可比回A'],
            ['M2 時間資訊完整性','標籤未成熟的樣本就是未來資訊；洩漏讓分數虛高','成熟清除t+h+1共1,386列；特徵只用t−1前；期限從使用者今天算'],
            ['M3 簡單基線優先','「不變價」「動量」是價格序列的硬對手','兩基線與模型同列；未勝動量如實呈現並限制宣稱'],
            ['M4 公開≠私人','市場均價不含店別資訊；公開t−7不是新增私人資料','A/B嚴格分離；增益須真店到期價驗證；不以0或均價代填'],
            ['M5 誤差≠效益','指標分數好不等於消費者決策變好','上漲召回10.1%限制「漲價提醒」；輸出必附驗證範圍與限制']],size=14.5,hsize=15.5)
        self.takeaway(s,'五個思維各有效應：契約、切分、基線、A/B與標示都由它們推導。',y=6.5)
        self.note(s,'深研究：五個核心思維',30,'整理菜價預測與零售分析的五個核心思維。可比性：不同店不同規格的價格不能直接比，零是無價不是零元。時間完整性：標籤沒成熟就是未來資訊，所以我們清了一千三百八十六列。簡單基線：不變價和動量很強，模型要先勝過它們才有複雜度的正當性。公開不等於私人：市場均價沒有店別資訊，把公開資料重包裝不會產生新資訊。誤差不等於效益：分數好不代表決策變好，上漲召回低就限制漲價提醒的用途。每個思維在講稿備註附了證據來源。',['G1','D2','E1','R02'],'思維是本案依查核證據整理的工作觀點，不宣稱所有專家都同意；證據細節見DEEP_RESEARCH.md Q1。')

    def p_controversies(self):
        s=self.page('深研究②：三個專業爭論','Deep Research 2/3','[G1] 雙方證據、共識與未解問題詳DEEP_RESEARCH.md Q2（數據在講稿備註）')
        groups=[
            ('① 市場均價能代表店價嗎？','共同趨勢訊號（批發→零售傳導）','店家仍有個別差異（私有紀錄含額外資訊）','A／B並列，真店到期價裁決'),
            ('② 複雜ML一定比較好嗎？','非線性、多特徵能力','簡單基線很強（持平多數下更難勝）','先跟不變價、動量比較再談價值'),
            ('③ 加更多資料一定更準嗎？','氣象／私人資料可能提供訊號','增益必須用實驗證明（消融／配對）','把「新增輸入是否有增益」直接當RQ2'),
        ]
        for i,(title,a,b,tw) in enumerate(groups):
            y=1.72+i*1.56
            self.box(s,.72,y,11.9,1.42,WHITE,LINE if i!=2 else ACCENT)
            self.text(s,.95,y+.10,11.4,.36,title,18,bold=True,tint=ACCENT)
            self.text(s,.95,y+.52,5.5,.72,'觀點A：'+a,14.5,linespace=1.12)
            self.text(s,6.60,y+.52,5.85,.72,'觀點B：'+b,14.5,linespace=1.12)
            self.text(s,.95,y+1.06,11.4,.32,'TW01：'+tw,14.5,bold=True,tint=ACCENT)
        self.takeaway(s,'三個爭論都沒有免費的答案——本案設計能裁決它們的實驗。',y=6.5)
        self.note(s,'深研究：三個專業爭論',35,'第一，公開均價夠不夠估店價：傳導存在——官方對二〇〇四到二〇〇九年颱風的分析顯示災後第一週批發均價平均上漲一成到四成、大數據平台用二十九億筆電子發票估零售；但均價沒有店別資訊——李岱鑫顯示含中盤商私有紀錄者誤差較低、本案資料無店ID。我們用A錨定加B差動量並列，讓真店到期資料裁決。第二，複雜模型是否勝過簡單基線：Team17的R平方最好品項零點八一、陳泯宏摘要有方向約六成；但本案凍結測試動量零點四二二六對模型零點四二一八、不變價MAE零點零四三六勝模型的零點零六六四——Team17未見基線對照。我們的立場是先勝基線再談價值。第三，加資料是否一定改善：氣象有理由但Team17未做消融、本案十二特徵也沒勝動量，李岱鑫的私有增益屬批發脈絡不能外推。我們把新增輸入的增益本身當成研究問題。',['G1','E1','W1','R02','R04','H17'],'雙方證據之查核層級見DEEP_RESEARCH.md Q2；「未見消融」指該簡報實讀頁未見，不斷言不存在。')

    def p_questions(self):
        s=self.page('深研究③：十個深問題','Deep Research 3/3','[G1] 十題全文與參考解答見附錄A4及DEEP_RESEARCH.md Q3')
        qs=['1 為何用macro-F1而非準確率？（Why）','2 為何預測相對變化、從今天起算？（Why）','3 輸入「一顆30元」或元/公斤會怎樣？（What-if）','4 公開資料截止日比今天舊很多呢？（What-if）','5 ±5%持平門檻調高調低的取捨？（Trade-off）','6 加氣象特徵值不值得？本案為何不加？（Trade-off）','7 上漲召回10.1%，系統還能用嗎？（Failure Case）','8 如何證明B真的有增益？為何不用回測？（Evidence）','9 Team17的R²與本案macro-F1能比嗎？（Comparison）','10 為何禁止LLM自己算菜價？颱風後系統如何反應？（Design/Real-world）']
        for i,q in enumerate(qs):
            self.text(s,.75,1.78+i*.46,7.6,.42,q,14.5)
        self.box(s,8.75,1.78,3.85,4.5,LIGHT,LINE)
        self.text(s,8.95,1.96,3.5,4.2,'類別覆蓋\n\nWhy ×2\nWhat-if ×2\nTrade-off ×2\nFailure Case ×1\nEvidence ×1\nComparison ×1\nDesign Decision ×1\n（含Real-world情境）\n\n每題附參考解答與\n推理重點，非背誦題。',14,linespace=1.28)
        self.takeaway(s,'能回答這十題，才算真的理解這個領域與本系統。',y=6.5)
        self.note(s,'深研究：十個深問題',15,'我們設計了十個深問題檢驗是否真正理解，涵蓋為什麼、如果、取捨、失敗案例、證據、比較與設計決策。例如：為什麼用宏平均F1而不是準確率、一把蔣一斤的單位問題、上漲召回只有一成時系統還能用嗎、怎麼證明B有增益、以及為什麼禁止語言模型自己算菜價。完整題目與參考解答在附錄。',['G1'],'十題與八類覆蓋見DEEP_RESEARCH.md Q3；答題重點在推理過程而非標準答案背誦。')

    def p_agent_principles(self):
        s=self.page('Agent設計原則：分工與安全','Agent設計 1/3','[AD1] docs/proposal_v5/AGENT_DESIGN.md；[C1] 教授要求（模型＋Domain Agent）')
        self.text(s,.75,1.62,11.8,.95,'核心原則（目標設計）：Agent自主選擇合適工具；ForecastEngine專責菜價預測；\n程式強制驗證；Agent根據真實工具結果解釋。現況：②為規則式固定序列。',19,bold=True,tint=ACCENT)
        self.table(s,.75,2.72,11.8,[3.7,4.1,4.0],[.42,1.38,1.38],[
            ['角色','職責','現況（依程式核對）'],
            ['③ ForecastEngine\n（計算者）','封存模型推論r̂；A錨定／B調整；\n維持資料與驗證邊界','CURRENT（模型包v0.1.0；\nfixtures 3/3重現）'],
            ['② Agent執行層\n（理解與調度）','規則解析（缺→追問）；固定序列呼叫2個\n白名單工具；模板回答（驗證器僅Qwen路徑）','CURRENT（parse_query＋get_market_quote／\npost_forecast＋227測試）；自主選工具與\nLLM Planner＝PROPOSED（暫緩）'],
            ],size=13.5,hsize=14.5)
        self.text(s,.75,6.02,11.8,.92,'安全要點：沒有ForecastEngine成功結果→不得自行產生數字；工具失敗→明確告知、不用LLM補值；AI不得竄改價格/方向/日期/來源；\n不得編造原因、準確率、機率或採購利益；白名單＋單查詢≤3次呼叫（已實作：2工具）；保存走/records API（未工具化）。',14,tint=WARN)
        self.note(s,'Agent設計原則',30,'教授要的是Domain Agent，不是聊天機器人或模型包裝。目標設計的分工是：預測引擎是唯一的計算者；Agent理解需求、選白名單工具、依結構化真值卡組裝回答。要誠實報告現況：目前已實作的是規則式原型——parse_query確定性解析、get_market_quote與post_forecast兩個有限工具、單查詢計數上限三次、模板回答（驗證器目前只掛在Qwen路徑，規則模板直接由工具事實逐字組文），tests兩百二十七項通過；工具呼叫是固定序列、不是自主選擇；保存走/records API、還沒封裝成Agent工具；LLM Planner屬未來暫緩。安全上，沒有工具成功結果就不能出數字，失敗就明說，不補值不編造。',['AD1','C1','A1'],'LLM後端（GLM/Qwen/Hermes）依使用者指示暫緩，本輪只做設計；不把規則原型寫成LLM Agent已完成；save_record工具化屬Proposed；逾時常數TOOL_TIMEOUT_SECONDS=10未接線於工具路徑，統一逾時屬Proposed。')

    def p_architecture(self):
        s=self.page('系統架構：五群組①–⑤＋暫緩未來區','Agent設計 2/3','[A1][AD1] 實線＝目前實際存在之元件與資料流；虛線＝PROPOSED（未實作/未部署）；數字為索引非順序')
        for x,y,w,h,head,body in [(.75,1.80,3.2,1.24,'① 使用者與手機','表單＋自然語言入口'),(5.05,1.80,3.2,1.24,'② Agent查詢處理','規則式（LLM屬虛線）'),(9.25,1.80,3.25,1.24,'③ 菜價計算','ForecastEngine＋A/B'),(9.25,4.00,3.25,0.98,'④ 公開歷史','市場均價・唯讀'),(5.05,4.00,3.2,0.98,'⑤ 預測紀錄','保存API・獨立儲存')]:
            self.box(s,x,y,w,h);self.text(s,x+.15,y+.14,w-.30,.38,head,18,bold=True,align='center');self.text(s,x+.15,y+.58,w-.30,.46,body,13,tint=MUTED,align='center',linespace=1.08)
        self.line(s,3.95,2.20,5.05,2.20,tint=ACCENT,width=1.6,arrow=True);self.text(s,3.98,1.82,.98,.3,'提交',12,align='center',tint=ACCENT)
        self.line(s,5.05,2.82,3.95,2.82,tint=ACCENT,width=1.6,arrow=True);self.text(s,3.95,3.10,1.1,.32,'回傳結果',12,align='center',tint=ACCENT)
        self.line(s,8.25,2.20,9.25,2.20,tint=ACCENT,width=1.6,arrow=True);self.text(s,8.25,1.82,.98,.3,'計算',12,align='center',tint=ACCENT)
        self.line(s,9.25,2.82,8.25,2.82,tint=ACCENT,width=1.6,arrow=True);self.text(s,8.22,3.10,1.06,.32,'回傳預測',12,align='center',tint=ACCENT)
        self.line(s,10.86,3.04,10.86,4.00,tint=ACCENT,width=1.6,arrow=True);self.text(s,11.03,3.40,1.2,.34,'唯讀載入',12,tint=ACCENT)
        self.line(s,5.98,3.04,5.98,4.00,tint=ACCENT,width=1.6,arrow=True);self.text(s,4.58,3.38,1.28,.56,'自願保存',12,tint=ACCENT,align='right')
        self.line(s,7.30,4.00,7.30,3.04,tint=ACCENT,width=1.6,arrow=True);self.text(s,7.45,3.40,.9,.34,'查閱',12,tint=ACCENT)
        self.text(s,.75,3.30,3.2,.9,'現況工具：get_market_quote、\npost_forecast（②固定序列）；\n保存經Web另呼 /records。',12.5,tint=MUTED,linespace=1.15)
        dz=self.box(s,.75,5.12,11.75,.78,WHITE,ACCENT,dash=True)
        self.text(s,.95,5.24,11.35,.56,'PROPOSED（虛線，未實作未部署）：LLM Planner／自主選工具／save_record工具化；GLM API・Qwen3.8-27B・Hermes＝②的語言層（非猜菜價）；SERVER_3090',13.5,tint=ACCENT)
        self.line(s,6.65,3.04,6.65,5.12,tint=ACCENT,width=1.4,arrow=True,dash=True)
        self.text(s,.75,6.04,11.85,.34,'圖例：實線＝現況已存在（規則式②、兩工具、ForecastEngine、/records保存API）；虛線＝PROPOSED。④⑤之間無連線（公開與私人儲存分離）。',12,tint=MUTED)
        self.text(s,.75,6.50,11.85,.34,'LLM只進②的語言層；菜價一律由③計算——此界線不因後端替換而改變。',16.5,bold=True,tint=ACCENT)
        self.note(s,'系統架構（五群組）',40,'請按編號看。①使用者以表單或自然語言提交查詢；②Agent查詢處理檢查必要資訊與單位、驗證上週價可比性，通過後呼叫③；③預測引擎唯讀載入④的公開歷史，用封存模型算出相對變化並做A與B，結果回②；②組裝附期限、截止日、來源與狀態的回答回①。使用者自願保存時走／records保存API寫入⑤，與④完全分離——保存目前由網頁另行呼叫、還不是Agent工具。實線都是目前實際存在的元件與資料流：規則式②、get_market_quote與post_forecast兩個工具、預測引擎、保存API。虛線是Proposed：LLM Planner、自主選工具、save_record工具化、GLM、Qwen、Hermes與SERVER，都還沒實作或還沒部署，而且LLM只掛在②的語言層、不用來猜菜價。',['A1','AD1','M2'],'①→②提交、②→③計算、③→④唯讀、③→②回傳、②→①回答、②→⑤保存/查閱（保存現況經Web／records，非Agent工具）。LLM後端與工具抽象屬Proposed，不宣稱已驗收。')

    def p_flowchart(self):
        s=self.page('查詢流程圖：十類決策分支（Proposed Agent）','Agent設計 3/3','[AD1] 流程圖描述目標系統；節點標CURRENT／PARTIAL；未標注＝CURRENT；完整對照見附錄A5')
        chain=[('使用者輸入（NL／表單）',0),('◇ D1 必要資訊齊全？（品項+價+單位+日期）',0),('◇ D2 單位可換算？（台斤原生／公斤×0.6）',0),('◇ D3 有上週同店價？',0),('◇ D4 同店價可比？（五重檢查）',0),('◇ D5 公開資料足夠且未過期？',0),('□ T1 呼叫 call_forecast＝post_forecast（CURRENT）',0),('◇ D6 工具成功？（422／503／逾時）',0),('◇ D7 證據與限制檢查（驗證器）',0),('□ R1 回答＋期限＋來源＋限制標示（模板）',0),('◇ D8 使用者自願保存？（PARTIAL）',0),('◇ D9 到期（t+7/t+14）可取得同店真價？（PARTIAL）',0),('□ T3 到期核對：A/B vs 同店實價（PARTIAL）',0)]
        sides={0:('追問缺失欄位（不猜測、不代填）',1),2:('拒絕並說明：顆/把無重量，請改台斤或公斤',0),3:('無→僅A（仍可預測）',1),4:('不可比→降級僅A＋說明原因',0),5:('明確「資料不足/過期」＋資料截止日',0),7:('明確錯誤碼；不用LLM補值',0),8:('不通過→改寫為忠實版本',0),10:('是→保存：走/records API（未封裝為AgentTool）',0),11:('缺（缺貨/換規格/未訪價）→記「無法核對」（≠未漲）',0)}
        x0,w0,pitch,y0,h=0.72,4.8,0.415,1.58,0.34
        for i,(t,is_d) in enumerate(chain):
            y=y0+i*pitch
            if is_d:self.box(s,x0,y,w0,h,LIGHT,ACCENT)
            else:self.box(s,x0,y,w0,h,WHITE,LINE)
            self.text(s,x0+.12,y+.033,w0-.24,h-.05,t,11.5,bold=bool(is_d),tint=ACCENT if is_d else INK,linespace=1.0)
            if i<len(chain)-1:self.line(s,x0+w0/2,y+h,x0+w0/2,y+pitch,tint=ACCENT,width=1.3,arrow=True)
        for i,(t,is_ok) in sides.items():
            y=y0+i*pitch
            self.line(s,x0+w0,y+h/2,x0+w0+.28,y+h/2,tint=MUTED,width=1.1,arrow=True)
            self.text(s,x0+w0+.58,y+.02,6.3,h-.04,t,11,tint=MUTED,linespace=1.0)
        self.text(s,6.15,6.54,6.5,.42,'未標注＝CURRENT；D5＝PARTIAL（>3日僅警告，無特徵才拒）；D7驗證器僅Qwen路徑\nD8/D9/T3＝PARTIAL（API與機制有，orchestration屬Proposed）；LLM＝PROPOSED',11,tint=MUTED,linespace=1.12)
        self.note(s,'查詢流程圖',30,'這張流程圖描述目標系統，節點會標注現況。主流程：先檢查必要資訊——品項、價格、單位缺了就追問，日期沒提供則以系統今天預填、只有明示但無法解析的日期才追問；單位不能換算就拒絕並說明；有上週價才做可比性檢查，不可比就降級只剩A；公開資料目前是落後超過三天先警告、該品項該市場沒有可用特徵才明確拒絕；然後呼叫白名單工具——現在對應post_forecast，失敗就報錯不補值；回答層的模板由工具事實逐字組文，驗證器目前只掛在Qwen路徑。最後三個節點是PARTIAL：保存走／records API、還沒封裝成Agent工具；到期核對的機制有、真店真值還沒收集。右側是每個分支的具體行為。',['AD1','A1'],'流程圖為Proposed Agent Flowchart；節點標注依實際程式核對（AGENT_DESIGN §7）；「除了LLM之外全部完成」的概括不成立；嚴格資料過期hard gate屬Proposed。')

    def p_pseudocode(self):
        s=self.page('Algorithm 1：TW01 Domain Price Agent（主講10步）','Agent設計（續）','[AD1] 完整41行版見附錄A5與AGENT_DESIGN.md §8；LLM不計算菜價')
        self.text(s,.72,1.52,11.9,.30,'Input：訊息M／今日t／白名單W　Output：回答R、追問Q、受控錯誤E、凍結紀錄P。步驟標CURRENT／PARTIAL／PROPOSED。',13,tint=MUTED)
        steps=[
            ('01','理解請求（Understand request）','CURRENT'),
            ('02','驗證必要資訊，缺則追問（Validate required information）','CURRENT'),
            ('03','選擇白名單工具（Select allowed tool）','PARTIAL（現況固定序列）'),
            ('04','取得公開資料（Retrieve public data）','CURRENT（get_market_quote）'),
            ('05','呼叫 ForecastEngine（Call ForecastEngine）','CURRENT（post_forecast）'),
            ('06','套用領域規則：單位／可比性／A／B（Apply domain rules）','CURRENT'),
            ('07','驗證結構化結果（Validate structured result）','CURRENT（驗證器）'),
            ('08','產生忠實解釋（Generate faithful explanation）','PARTIAL（模板；LLM屬PROPOSED）'),
            ('09','使用者同意則保存（Save prediction if approved）','PARTIAL（/records；未工具化）'),
            ('10','到期以店價核對（Verify against future store price）','PARTIAL（機制有；T16真值未有）'),
        ]
        y=1.98
        for ln,txt,status in steps:
            self.text(s,.72,y,.62,.3,ln,13,bold=True,tint=MUTED,font=MONO,linespace=1.0)
            self.text(s,1.40,y,8.0,.3,txt,15,linespace=1.0)
            tint=WARN if 'PROPOSED' in status else (MUTED if status.startswith('PARTIAL') else ACCENT)
            self.text(s,9.5,y,3.1,.3,status,11.5,bold=True,tint=tint,linespace=1.0)
            y+=0.40
        self.text(s,.72,6.08,11.9,.52,'CURRENT對應實際程式：parse_query／get_market_quote／post_forecast／RuleBackend模板（tests 227項；驗證器僅掛Qwen路徑）。\nPARTIAL：保存走/records（未工具化）、到期機制有真值未有；PROPOSED：LLM Planner與LLM解釋、嚴格資料過期hard gate（暫緩）。',12.5,tint=MUTED)
        self.text(s,.72,6.62,11.9,.32,'LLM不算菜價：數字一律出自ForecastEngine與驗證後的工具輸出。',15.5,bold=True,tint=ACCENT)
        self.note(s,'演算法一（主講10步）',20,'主講版把演算法壓成十步：理解、驗證、選工具、取公開資料、呼叫預測引擎、套領域規則、驗證結果、忠實解釋、自願保存、到期核對。每步標注現況：現況的固定序列對應get_market_quote與post_forecast兩個工具加模板回答——驗證器目前只掛在Qwen路徑，規則模板直接由工具事實逐字組文；保存與到期核對是PARTIAL——保存API有但還不是Agent工具、真店真值還沒收集；LLM Planner、LLM解釋與嚴格的資料過期強制拒絕屬PROPOSED。完整四十一行逐行版在附錄。重點不變：語言模型不算菜價，數字一律出自預測引擎與驗證後的工具輸出。',['AD1','A1'],'α=0.3為固定實驗規則（未訓練）；完整版41行含Input/Output與邊界聲明見附錄A5；Pseudocode↔實作映射見AGENT_DESIGN §8。')

    def p_data(self):
        s=self.page('資料來源與整理','資料與方法','[D1] 臺中市政府公開資料快照；[D2] 既有資料品質與標籤統計')
        self.table(s,.75,1.74,11.85,[2.62,9.23],[.46,.80,.80,.80,.80,.80],[['項目','本案使用範圍'],['來源','臺中市公有零售市場每日訪價均價（data.gov.tw 84539）'],['期間／市場','2025-10-04～2026-10-02；排除停用市場後13市場'],['品項','甘藍、青江白菜、絲瓜'],['單位／缺值','元／台斤；0代表無報價，不是零元（前三品項905格轉缺測）'],['整理方式','統一日期與單位；建立同市場、同品項的7／14天到期配對']],size=19)
        self.takeaway(s,'一筆資料代表市場訪價均價，不代表其中某一家店的成交價。',y=6.5)
        self.note(s,'資料來源與整理',25,'資料是臺中市十三個公有零售市場的每日訪價均價，期間約一年。單位是元每台斤，零代表無報價、不是零元，所以九百零五格零值轉為缺測。整理後依同市場、同品項、同日期建立七天與十四天的到期配對。沒有單店識別，公開測試與單店效果必須分開解釋——這是A/B設計的出發點。',['D1','D2'],'原始4,450列×63欄；原三品項長表13,350列；364是原檔不同日期數，不表示每市場每日無缺。')

    def p_target(self):
        s=self.page('預測目標：從報價日算起的7／14天變化','資料與方法','[M1] 固定日曆期限；±5%含邊界為持平；下方數值均為教學例')
        for x,head,sub in [(1,'t','本次報價日'),(6,'t＋7','7個日曆日後'),(10.35,'t＋14','14個日曆日後')]:
            self.text(s,x,1.85,2,.5,head,26,bold=True,tint=ACCENT,align='center');self.text(s,x-.35,2.47,2.7,.4,sub,17,align='center')
        self.line(s,2,3.12,11.35,3.12,tint=ACCENT,width=1.8,arrow=True)
        for x in [2,7,11.35]:self.line(s,x,2.99,x,3.26,tint=ACCENT,width=1.8)
        self.text(s,1,3.62,11.35,.6,'相對變化 ＝（到期價格 − 當日價格）÷ 當日價格',23,bold=True,align='center')
        self.table(s,.90,4.5,11.50,[3.83,3.84,3.83],[.58,.77],[['下跌','持平','上漲'],['小於 −5%','介於 −5% 與 ＋5%','大於 ＋5%']],size=21)
        self.text(s,.95,6.28,11.4,.48,'例如市場均價40→43元：＋7.5%，上漲；40→42元：＋5%，持平。',18,tint=ACCENT)
        self.note(s,'預測目標與漲跌定義',30,'我們不預測模糊的下週平均，而是從本次可信報價日起算，精確七天與十四個日曆日。相對變化就是到期價減當日價除以當日價。超過正負百分之五才算漲或跌，剛好百分之五仍屬持平。四十變四十三是百分之七點五上漲；變四十二剛好百分之五，持平。公開資料用市場均價建標籤，同店驗證要用同店到期價。',['M1'],'正式分類含eps=1e-9浮點容差；t不是公開行情最後日期；同店真值另收，不以市場值代填。')

    def p_a_mode(self):
        s=self.page('A模式：沒有上週價，也能查','核心方法 1/2','[M2] 現價錨定方法；本頁全部數值為教學假設，非真店實驗或模型fixture')
        self.text(s,.8,1.85,11.7,.5,'今天店價 ×（1＋模型估計的相對變化）＝ 到期價格估計',22,bold=True)
        self.text(s,.8,2.68,11.7,.5,'假設今天32元／台斤；模型的7天估計為 −4.1%。',21)
        self.text(s,.8,3.36,11.7,.6,'32 ×（1 − 0.041）＝ 30.688 ≈ 30.7元',26,bold=True,tint=ACCENT)
        self.table(s,.82,4.42,11.69,[3.2,3.2,3,2.29],[.55,.60,.60],[['期限','假設相對變化','價格估計','方向'],['7天','−4.1%','30.7元','持平'],['14天','−0.9%','31.7元','持平']],size=19)
        self.text(s,.83,6.35,11.7,.34,'輸入現價改變金額尺度，不會讓方向預測自動變準。',18,bold=True,tint=ACCENT)
        self.note(s,'A模式',30,'A模式不需要上週紀錄。假設今天三十二元，模型估計七天相對變化負百分之四點一，三十二乘以零點九五九得到三十點六八八，顯示約三十點七元；仍在正負百分之五內，分類持平。十四天同理。這些是教學假設。現價錨定只改顯示金額：p大於零時，錨定後的相對變化恆等於模型的相對變化，方向分類不變——這是代數性質，不是準確率實驗。',['M2','M1'],'A公式p̂=p(1+r̂)；[p(1+r̂)−p]/p=r̂；sign(r̂)<0不等於down（−4.1%仍flat）。')

    def p_b_mode(self):
        s=self.page('B模式：多一筆上週價，是否真的有幫助？','核心方法 2/2','[M2] α＝0.3為固定實驗規則；本頁所有價格與變化數字均為教學假設')
        self.text(s,.8,1.83,11.72,.6,'在A的基礎上，加上「店價變化與公開市場變化的差」。',22,bold=True)
        self.table(s,.8,2.72,6.1,[3,3.1],[.60,.64,.64,.64],[['教學條件','數值'],['今天／上週店價','32元／28元'],['店價週變化','32 ÷ 28 − 1 ≈ 14.29%'],['公開同期變化','假設為 ＋1%']],size=18)
        self.text(s,7.48,2.71,4.87,.48,'B的7天調整',21,bold=True,tint=ACCENT)
        self.text(s,7.48,3.48,4.8,1.5,'−4.1%\n＋0.3 ×（14.29% − 1%）\n≈ −0.11%　仍為持平',20)
        self.text(s,7.48,5.15,4.7,.62,'同店、同品項、同規格；\n日期與單位需可比較。',16,tint=MUTED)
        self.takeaway(s,'係數0.3不是學得的效果；B是否更好，要等同店到期價驗證。')
        self.note(s,'B模式',35,'有可比較的上週同店價才使用B。今天三十二、上週二十八，店價週變化約百分之十四點二九；公開同期假設百分之一。B把差乘以零點三加回A的負百分之四點一，得到約負百分之零點一一，仍屬持平——注意負零點一是接近零，不是接近門檻。零點三只是固定實驗規則，不是從同店資料學來的。B能不能更好，要同批案例同時保留A和B，等到期真值比較。',['M2','P1'],'r_B=r_A+0.3×(Δ店−Δ公)；上週可比日期7±2天；缺少或不可比則僅A，不用0或公開t−7冒充私人資料。')

    def p_selection(self):
        s=self.page('先用驗證集選模型，再看封存測試','評估設計','[M3, S1] 保留樣本涵蓋期；成熟清除規則及四段範圍見附錄A6')
        for x,w,label,span in [(.84,3.76,'訓練','2025-10-04～2026-05-08'),(4.76,3.76,'驗證','2026-05-10～2026-07-21'),(8.68,3.76,'測試','2026-07-22～2026-10-02')]:
            self.text(s,x,1.88,w,.46,label,22,bold=True,tint=ACCENT,align='center');self.line(s,x,2.55,x+w,2.55,tint=ACCENT,width=6);self.text(s,x-.05,2.88,w+.1,.42,span,15,align='center')
        self.table(s,.85,3.85,11.60,[2.45,4.6,4.55],[.57,.72,.72],[['期限','選定模型','選擇方式'],['7天','隨機森林（RF，300棵樹）','依驗證集macro-F1選型；'],['14天','梯度提升（HGB，200輪）','再以同一封存測試列比較基線']],size=20)
        self.takeaway(s,'特徵只使用當下可見的歷史；邊界樣本依到期可見性清除（1,386列）。')
        self.note(s,'模型選擇與評估設計',25,'評估順序：先訓練，再以驗證集的宏平均F1選型，最後才看保留測試。七天選隨機森林、十四天選梯度提升。輸入是十二個數值特徵加品項編碼。邊界上，標籤成熟日跨入下一段的樣本要清除——兩個邊界共一千三百八十六列，七天帶八日、十四天帶十五日。測試樣本七天兩千零八十五筆、十四天一千八百五十九筆。',['M3','S1'],'同日起算觀測不跨區隨機切分；依h分別清除；測試n(h7)=2,085、n(h14)=1,859。')

    def p_direction(self):
        E=self.eval['horizons']
        s=self.page('結果：方向分數仍未超過動量基線','初步結果 1/2','[E1] 封存測試：7天 n＝2,085；14天 n＝1,859；不同方法使用相同測試列')
        self.text(s,.82,1.85,11.7,.5,'方向macro-F1：上漲、持平、下跌分別計分後平均，越高越好。',19)
        self.table(s,.82,2.82,11.69,[6.19,2.75,2.75],[.62,.80,.80,.80],[['方法','7天','14天'],['不變價：全部預測持平',f"{E['h=7']['baselines']['flat_no_change']['direction']['macro_f1']:.4f}",f"{E['h=14']['baselines']['flat_no_change']['direction']['macro_f1']:.4f}"],['動量：過去同長度變化延續',f"{E['h=7']['baselines']['past_change_continues']['direction']['macro_f1']:.4f}",f"{E['h=14']['baselines']['past_change_continues']['direction']['macro_f1']:.4f}"],['本案選定模型',f"{E['h=7']['selected']['direction']['macro_f1']:.4f}",f"{E['h=14']['selected']['direction']['macro_f1']:.4f}"]],size=22,highlight=(3,))
        self.takeaway(s,'本案高於全持平，但兩個期限都未勝動量；不能只挑較弱基線。')
        self.note(s,'方向結果',35,'同一批封存測試列比較三種方法。不變價永遠預測持平；動量延續過去變化；最後是本案模型。七天零點四二一八、十四天零點四一六九，都高於全持平，但都沒有超過動量。所以不能只報告比全持平好就說成功。這裡沒有做顯著性檢定，不能把小數差異說成顯著勝出。負向結果會一路保留到結論。',['E1'],'macro-F1是三類F1非加權平均，不是準確率；RF/HGB不是LLM猜價；表格直接讀封存JSON。')

    def p_mae_recall(self):
        E=self.eval['horizons']
        s=self.page('結果限制：價格誤差與上漲事件仍需改善','初步結果 2/2','[E1] 相對變化MAE越小越好；數值不是元，也不是準確率')
        self.table(s,.85,1.85,11.6,[6.1,2.75,2.75],[.62,.82,.82],[['相對變化MAE','7天','14天'],['不變價',f"{E['h=7']['baselines']['flat_no_change']['return_mae']:.4f}",f"{E['h=14']['baselines']['flat_no_change']['return_mae']:.4f}"],['本案選定模型',f"{E['h=7']['selected']['return_mae']:.4f}",f"{E['h=14']['selected']['return_mae']:.4f}"]],size=22)
        self.text(s,.86,4.55,11.6,.56,'7天實際上漲158筆，模型抓到16筆（召回10.1%）。',22,bold=True)
        self.text(s,.86,5.3,11.6,.52,'方向與金額各有不足；目前不宜把它當成可靠的上漲警報。',20,tint=MUTED)
        self.takeaway(s,'先呈現能力邊界，再用真店與後續實驗判斷是否值得使用。')
        self.note(s,'誤差與上漲召回',30,'相對變化的平均絕對誤差，模型七天零點零六六四、十四天零點零九八三，都高於不變價——點估計未勝簡單基線，只供參考。上漲事件：七天實際一百五十八筆，模型只抓到十六筆，召回約一成；十四天更 低，約百分之八點六。模型偏保守報持平，這限制「漲價提醒」的價值，也決定後續要驗證什麼。不能保證依預測採買就省錢。',['E1'],'MAE為相對變化誤差（0.0664約6.64個百分點的變化量誤差）；h14上漲召回23/268≈8.6%。')

    def p_ui(self):
        s=self.page('介面示例：同一期限，對照A與B','原型展示','[U1] 2026-10-03本機原型，放大上方7天結果區；非本次即時查詢')
        cropped=self.evidence/'ui_7day_crop.png';im=Image.open(self.shot);im.crop((0,0,390,590)).save(cropped)
        s.shapes.add_picture(str(cropped),Inches(.95),Inches(1.72),height=Inches(4.9))
        self.points(s,[('先看期限','確認這組結果是7天，另一組才是14天。'),('再看A／B','對照不使用與使用上週資訊的結果。'),('最後讀範圍','市場均價、店價估計與實驗性提醒分開。')],x=5.35,y=2.0,w=7,size=21,gap=1.32)
        self.note(s,'介面示例',25,'這是本機原型的歷史截圖，不是今天重新查詢。為了讓字看清楚，這頁放大上方七天的A與B。讀畫面先看期限，再看有無使用上週資訊的差異，最後看來源與實驗性提醒。畫面中的B與前面教學例數值不同，來自另一個歷史查詢，不能混成同一筆。完整保存重播、語言模型後端與外網服務仍未驗收。',['U1','A1','P1'],'圖片只裁切放大7天比較；原圖390×844保留原位，不改數值或日期。')

    def p_plan(self):
        s=self.page('下一步：用對應證據回答三個問題','驗證計畫','[P1] 設計藍圖與DESIGN_DELTA；實際日期待定；本輪不啟動暫緩整合')
        self.table(s,.8,1.9,11.75,[2.6,5.0,1.9,2.25],[.5,1.3,1.3,1.3],[['要驗證什麼','需要的證據','目前','狀態說明'],['同店A／B增益（RQ2）','先保存A與B；7／14天後取得同店同規格實價','待執行','缺真店到期價（T16 HOLD）'],['低負擔與理解（RQ3）','輸入時間、錯誤率；能否說明期限與資料範圍','待執行','原型就緒，人因未測'],['服務是否可用','後端整合、外網手機查詢及端到端驗證','暫緩','依使用者指示；SERVER資訊未提供']],size=19)
        self.takeaway(s,'公開測試、同店驗證與系統可用性，是三種不同的證據。')
        self.note(s,'後續驗證',30,'後續驗證不是再訓練一次。第一，保存同一筆查詢的A與B，等七天十四天取得同店同規格真價，才比較輸入增益。第二，觀察使用者能否順利輸入並正確理解資料範圍。第三，後端與外網另做端到端驗證。三類證據不能互相代替。設計藍圖與OpenSpec保留在專案；本輪不啟動暫緩的整合工作。',['P1','DD1'],'同筆A/B配對先凍結再取到期真值；不用公開t−7或均價代替私人到期資料。')

    def p_conclusion(self):
        s=self.page('結論','結論','TW01｜Proposal v5｜主講結束；後附文獻摘要、深研究、計算與引用')
        self.points(s,[('已完成','公開市場7／14天評估（含負向）、A／B原型與Domain Agent三種設計表示。'),('目前限制','方向未勝動量、誤差未勝不變價、上漲召回低；同店效果零證據；LLM後端暫緩。'),('下一步','取得同店到期真值回答B增益；人因與部署驗證依計畫推進。')],y=2.0,gap=1.4,size=23)
        self.text(s,.75,6.3,11.8,.5,'交付的是誠實、可驗證的預測與增益評估框架——不是「很準的預測」。',19,bold=True,tint=ACCENT)
        self.note(s,'結論',20,'總結：我們把現場報價連到固定七天十四天的預測任務，完成公開評估、A/B原型，以及符合Domain Agent要求的架構、流程圖與虛擬碼設計。限制同樣清楚：方向未勝動量、誤差未勝不變價、同店效果還沒有證據。下一步是取得同店到期真值，回答多一筆上週價有沒有幫助。謝謝，附錄備有完整文獻表、深研究與計算細節。',['P1','E1'],'本版為作者自驗候選，待ChatGPT獨立複審；不更換題目或模型。')

    # ---------- appendix ----------
    def _summary_rows(self,ids):
        rows=[['Ref.','Year','Problem','AI Method','Domain Knowledge','Dataset','Findings','Limitation']]
        data={
         'R01':['R01','2024','大宗蔬菜批發價預測','ARIMA/ETS/TDNN/LSTM比較','批發價格結構、季節性、前期資訊','台灣批發2012–2022（11年）','摘要列RMSE/MAD/MAPE與方向正確率；甘藍前1期LSTM方向約6成','批發非店價；無固定7/14期限；全文解禁前僅摘要'],
         'R02':['R02','2015','私有資料對下週批發價預測的價值','時間序列；含/不含私有組合對照','供應鏈私有紀錄（中盤商筆記）vs公開登記','高雄果菜公司66週','含私有者誤差較低（指標UNKNOWN）；\n私有資料有價值','批發脈絡；小樣本；回測非前瞻'],
         'R03':['R03','2017','零售市場菜價趨勢與區間','希爾伯特-黃變換（HHT）','零售均價非線性/非平穩結構','高雄公有零售市場均價','以HHT析趨勢與區間（指標UNKNOWN）','市場均價非單店；無固定期限；全文未取得'],
         'R04':['R04','2018','農產品零售價估計與產銷脈動','電子發票大數據估計＋情境模擬','批發×零售(通路段)橋接；颱風情境','台灣104–106年29億筆電子發票','15項農產零售估計模型；模擬颱風影響','通路段估計非店價；內部導向；無消費者輸入'],
         'R05':['R05','2026','菜價行情查詢與AI預報','未公開（UNKNOWN）','批發行情＋氣象資料；零售換算/價格溫度計文案','全台批發行情（官網稱至2026-10-03）','官網明列中長期趨勢預測等功能文案','未安裝實測；模型/指標/期限不透明'],
         'R06':['R06','2026','輸入購買價比對當日行情','換算比對（非預測模型）','台斤/公斤換算；當日行情基準','農糧署農產品交易行情','證明現場輸入價格需求存在','止於當日比對；其他功能UNKNOWN'],
         'R07':['R07','2025','氣候×菜價關聯探勘','決策樹探勘','氣候資料與菜價之領域關聯','氣候資料＋台灣蔬菜價格（爬蟲+MySQL）','決策樹探勘氣候與菜價關聯（指標UNKNOWN）','課程專題；探勘非期限預測；無到期驗證'],
         'R10':['R10','2026','GenAI＋預測ML之農產產銷決策（徵件）','徵件公告（非成果）','農業產銷開放資料應用脈絡','農業產銷開放資料','官方政策動向：方向獲重視','公告非成果；生產端導向'],
         'H17':['H17','2025','蔬果價格預測與採購指南','LightGBM×6品項；Early Stopping 50；滾動驗證','批發上/中/下價×交易量＋產地氣象（5要素；3/7/30天累積、極端指標、季節性）；防洩漏原則','批發行情站＋歷史氣象觀測庫；訓練2018–2022/驗2023/測2024','2024測試R²：小白菜0.8061、芥藍0.7744、茼蒿0.7211、菠菜0.5281、甘藍0.4444、芹菜0.4068；未來五日預測＋採購建議＋食譜','市場層級無店價輸入；五天非7/14日曆天；未見基線/消融；單位未標；未經重現'],
         'W1':['W1','2010','颱風豪雨後批發價量變動分析','官方統計回溯（非ML）','災後價格復原時間結構（1–3週）；品項差異','2004–2009全台批發每週均價與交易量','災後第1週均價平均+10–40%、第2週+30–90%、第3週約2倍；甘藍第1週1.2–1.7倍','全台批發週均價歷史統計；非零售/店價；非本案期間'],
         'TW01':['TW01','2026','現場單店報價之7/14天方向預測與輸入增益','RF(7天)/HGB(14天)＋A錨定/B差動量(α=0.3)；Domain Agent(規則式)','均價≠店價；±5%門檻；台斤換算；可比性五重檢查；成熟清除t+h+1','臺中13市場2025-10-04～2026-10-02（data.gov.tw 84539）','macro-F1 0.4218/0.4169勝持平未勝動量；MAE未勝不變價；上漲召回10.1%/8.6%；A/B協議就緒增益零證據','僅一年臺中；B未驗證；LLM後端暫緩；人因未測'],
        }
        for i in ids:rows.append(data[i])
        return rows

    def p_sum_full_1(self):
        s=self.page('附錄A1｜文獻摘要表（R01–R04）','附錄','[G1] 八欄格式；來源與查核層級明細見A3；UNKNOWN＝未載明非「沒有」')
        self.table(s,.55,1.70,12.25,[.78,.76,1.52,1.60,1.70,1.56,2.16,2.17],[.38,1.18,1.18,1.18,1.18],self._summary_rows(['R01','R02','R03','R04']),size=10.5,hsize=11)
        self.note(s,'附錄A1 文獻摘要（上）',0,'八欄表前四件：兩篇學術（批發預測、私有資料價值）、一篇零售均價分析、一個官方零售估計平台。閱讀重點是Domain Knowledge欄與Limitation欄的對照——方法各異，但都未觸及消費者現場店價。',['G1','R01','R02','R03','R04'],'完整來源URL與讀取層級見A3與docs/proposal_v5/ARTICLE_SUMMARY_TABLE.md。')

    def p_sum_full_2(self):
        s=self.page('附錄A2｜文獻摘要表（R05–R10）','附錄','[G1] 產品與政策動向；未安裝實測；文案非效果證據')
        self.table(s,.55,1.70,12.25,[.78,.76,1.52,1.60,1.70,1.56,2.16,2.17],[.38,1.18,1.18,1.18,1.18],self._summary_rows(['R05','R06','R07','R10']),size=10.5,hsize=11)
        self.note(s,'附錄A2 文獻摘要（中）',0,'產品端兩件（預測文案與當日比對）、課程探勘一件、官方徵件一件。產品未公開的欄位一律標UNKNOWN，不寫「沒有」。',['G1','R05','R06','R07','R10'],'R10為公告非成果，不入方法比較。')

    def p_sum_full_3(self):
        s=self.page('附錄A3｜文獻摘要表（H17/W1/TW01）＋查核層級','附錄','[G1][H17][W1] 本案自列於末行；分數不跨資料集比較')
        self.table(s,.55,1.66,12.25,[.78,.76,1.52,1.60,1.70,1.56,2.16,2.17],[.38,1.28,1.28,1.28],self._summary_rows(['H17','W1','TW01']),size=10.5,hsize=11,highlight=(3,))
        self.text(s,.62,6.02,12.2,.85,'查核層級：R01/R02/R03＝摘要實讀；R04＝報導全文；R05/R06/R07＝官網/商店/repo頁；R10＝公告全文；H17＝原PDF第一手逐頁影像閱讀11/15頁（2026-10-08；餘4頁依同批筆記）；W1＝官網全文；TW01＝本機凍結工件重核。',12.5,tint=MUTED)
        self.note(s,'附錄A3 文獻摘要（下）與查核層級',0,'最後三列：課程前作Team17、官方災後分析、與本案自列。每件的查核層級列於下方——摘要實讀、報導全文、官網頁面或本機工件，等級不同、主張強度不同。跨列不排名。',['G1','H17','W1','E1'],'TW01自列供對照，非文獻；完整明細見docs/proposal_v5/ARTICLE_SUMMARY_TABLE.md。')

    def p_ten_questions(self):
        s=self.page('附錄A4｜十個深問題（全文）','附錄','[G1] 參考解答與推理重點見docs/proposal_v5/DEEP_RESEARCH.md Q3')
        qs=[('1〔Why〕','為何用macro-F1而非準確率？→ 近九成持平下，全猜持平accuracy≈0.81但macro-F1僅0.30，指標須抗多數類主導。'),('2〔Why〕','為何預測相對變化、從今天t起算？→ 決策基準是眼前價格；固定日曆天讓到期可核對；起點漂移會破壞可驗證性。'),('3〔What-if〕','輸入「一顆30元」或元/公斤？→ 無重量單位拒絕並說明；公斤×0.6換算保留原值；非正數422。'),('4〔What-if〕','公開資料比今天舊很多？→ 期限仍從今天算；標示截止日與落後；過大走「資料過期」明確降級。'),('5〔Trade-off〕','±5%門檻調高調低？→ 高：事件少而扎實；低：事件多但標籤噪聲放大；凍結在先、敏感度在後。'),('6〔Trade-off〕','加氣象特徵值不值得？→ 有依據但無消融保證；先勝基線再疊特徵；列為未來實驗。'),('7〔Failure〕','上漲召回10.1%還能用嗎？→ 漏報上漲是最大限制；可用部分：整體方向訊號與低誤報；改善列後續計畫。'),('8〔Evidence〕','如何證明B有增益？為何不用回測？→ 事前凍結A/B＋同店到期實價配對；公開t−7測不出私人增益。'),('9〔Comparison〕','Team17 R²與本案macro-F1能比嗎？→ 任務/資料/指標/基線皆不同，不能換算；跨作品比較須同資料同協議重現。'),('10〔Design〕','為何禁止LLM算菜價？颱風後系統如何反應？→ 可追溯性要求数字出自工具；颱風情境如實標示資料截止與召回限制。')]
        for i,(tag,q) in enumerate(qs):
            y=1.72+i*.505
            self.text(s,.72,y,1.72,.44,tag,13,bold=True,tint=ACCENT)
            self.text(s,2.50,y,10.2,.48,q,12.5,linespace=1.05)
        self.note(s,'附錄A4 十個深問題',0,'十題全文。每題的完整參考解答與推理重點在深研究文件第三節。題目覆蓋八類認知層次，檢驗的是理解而非背誦。',['G1'],'答案口徑與主文一致；推理重點強調「先看證據結構再下結論」。')

    def p_algo_full(self):
        s=self.page('附錄A5｜Algorithm 1 完整版（41行）','附錄','[AD1] 行02/27（棕）＝未來LLM環節（暫緩）；行32–34＝PARTIAL（/records有、未工具化）；行37–41＝機制有、T16真值未有')
        code=[
            ('01','procedure TW01_AGENT(M, t, W)  // M=使用者訊息; W=白名單工具集',0),
            ('02','  S ← PARSE_REQUEST(M)   // ② 現況:規則式(未來:LLM Planner,經schema驗證)',1),
            ('03','  if S 缺 品項∨今天價∨單位∨日期 then',0),
            ('04','      return Q ← 追問缺失欄位  // D1;不猜測、不代填',0),
            ('05','  end if',0),
            ('06','  u ← NORMALIZE_UNIT(S.單位)  // 台斤原生;公斤×0.6換算保留原值',0),
            ('07','  if u 不可換算(顆/把/袋 無重量) then',0),
            ('08','      return E ← 「單位不可換算,請改元/台斤或元/公斤」  // D2',0),
            ('09','  end if',0),
            ('10','  comparable ← CHECK_COMPARABILITY(S.上週價)  // 五重檢查',0),
            ('11','  if S.上週價 存在 ∧ ¬comparable then',0),
            ('12','      mode ← "A"; 警示 ← 「上週價不可比(原因),本次僅A」  // D4',0),
            ('13','  else if S.上週價 存在 then',0),
            ('14','      mode ← "both"  // D3: A/B並列',0),
            ('15','  else',0),
            ('16','      mode ← "A"  // 無上週價仍可預測',0),
            ('17','  end if',0),
            ('18','  if ¬DATA_FRESH() then  // 引擎內建:截止日/不足檢查',0),
            ('19','      return E ← 「資料不足/過期(截止日=…),本次無法預測」  // D5',0),
            ('20','  end if',0),
            ('21','  F ← CALL_TOOL(call_forecast, S, mode)  // ③ 唯一計算者;現況=post_forecast',0),
            ('22','  if F 失敗 then',0),
            ('23','      return E ← 錯誤碼＋「本次無法預測」  // D6 不用LLM補值',0),
            ('24','  end if',0),
            ('25','  // F內部(③): ④唯讀→模型 r̂_7/r̂_14→A=p(1+r̂)→(both)B=r_A+0.3×(Δ店−Δ公)',0),
            ('26','  card ← TRUE_VALUE_CARD(F)  // 結構化真值卡:數字/方向/日期/來源 唯讀',0),
            ('27','  draft ← COMPOSE(card)  // ② 現況:模板;未來:LLM依card生成',1),
            ('28','  if ¬VALIDATE(draft, card) then',0),
            ('29','      draft ← REWRITE_FAITHFUL(card)  // D7:擋誇大/未驗證數字/方向衝突',0),
            ('30','  end if',0),
            ('31','  R ← draft＋期限(t+7,t+14)＋資料截止日＋target/validation_scope＋限制',0),
            ('32','  if 使用者自願保存 then',0),
            ('33','      P ← CALL_TOOL(save_record, S, F)  // ⑤;PARTIAL:現況走/records API',0),
            ('34','  end if',0),
            ('35','  return R (,P)',0),
            ('36','end procedure',0),
            ('37','procedure EXPIRE_CHECK(P, t+7/t+14)  // D9;機制有,T16真值未收集',0),
            ('38','  g ← 取同店同品項同規格到期實價',0),
            ('39','  if g 缺(缺貨/換規格/未訪價) then return 「無法核對」(≠未漲)',0),
            ('40','  return 配對比較 A/B vs g(方向一致率、誤差)  // 增益＝同案例A、B之差',0),
            ('41','end procedure',0),
        ]
        y=1.56
        for ln,txt,future in code:
            self.text(s,.55,y,.52,.22,ln,9,bold=True,tint=MUTED,font=MONO,linespace=1.0)
            self.text(s,1.08,y,11.85,.22,txt,9,tint=WARN if future else INK,font=MONO,linespace=1.0)
            y+=0.127
        self.note(s,'附錄A5 Algorithm 1 完整版',0,'完整四十一行逐行版，與主講十步版、流程圖、架構圖同一套編號對應。棕色行是未來LLM環節；保存段是PARTIAL——保存API有、還沒封裝成Agent工具；到期核對段機制有、真店真值未收集。完整映射表在AGENT_DESIGN第八節。',['AD1'],'Pseudocode↔現有實作映射見AGENT_DESIGN.md §8（parse_query／get_market_quote／post_forecast／驗證器／records等）；α=0.3未訓練。')

    def p_purge(self):
        s=self.page('附錄A6｜資料口徑與成熟清除','附錄','[D2, S1] 既有標籤與切分資料；本版唯讀使用')
        rows=[['邊界／期限','清除起算日範圍','列數']]
        for boundary,label in [('train_to_val','訓練→驗證'),('val_to_test','驗證→測試')]:
            for h in ['h7','h14']:
                r=self.stats['purge']['segments'][boundary][h];rows.append([f'{label}／{h[1:]}天',f"{r['t_min']}～{r['t_max']}",str(r['rows'])])
        self.table(s,.8,1.82,11.73,[3.55,5.86,2.32],[.6,.61,.61,.61,.61],rows,size=18)
        self.text(s,.86,5.15,11.65,1.0,'成熟日＝t＋h＋1；四段合計1,386列，聯集30個起算日；7天清除帶8日、14天15日。\n7天有效標籤10,952筆；14天10,680筆，與測試樣本數不同。',18)
        self.note(s,'附錄A5 資料與成熟清除',0,'成熟清除的日期與母體。七天對應t加八、十四天對應t加十五，分別清除跨界的標籤。不同期限清除帶長度不同，不能當成同一條空檔。',['D1','D2','S1'],'21筆浮點邊界差異之說明見run3證據；不改labels。')

    def p_formulas(self):
        s=self.page('附錄A7｜A／B公式與可比條件','附錄','[M1–M2] 使用固定α＝0.3，不宣稱係數已學得或已驗證有增益')
        self.text(s,.84,1.88,11.6,.5,'A：p̂(t＋h) ＝ p(t) ×（1＋r̂_h）',23,bold=True)
        self.text(s,.84,2.72,11.6,.55,'B：r_B ＝ r_A ＋ 0.3 ×（Δ店價 − Δ公開同期）',23,bold=True)
        self.text(s,.87,3.72,11.6,1.2,'p(t)：今天店價；r_A：公開模型的相對變化估計。\nΔ店價：今天價 ÷ 上週價 − 1；公開同期使用可比期間。\n上週價要有實際日期，並確認同店、同品項、同規格與單位。',18)
        self.text(s,.87,5.42,11.6,.95,'p＞0時，[p(1＋r̂)−p]／p＝r̂。\n同一分類器下，A錨定只改金額；缺少可比上週資訊則回A。',19,tint=ACCENT)
        self.note(s,'附錄A6 公式',0,'A的方向不變是代數性質，不是準確率實驗。B加上差動量後可改變相對變化，但是否更接近真店到期價仍要驗證。',['M1','M2'],'7±2天為可比上週日期契約；單位先轉同尺度。')

    def p_by_crop(self):
        s=self.page('附錄A8｜分品項方向結果','附錄','[E2] 公開市場封存測試；不以事件比例解釋分數差異的因果')
        rows=[['品項','7天：n／macro-F1','14天：n／macro-F1']]
        for crop,cn in [('cabbage','甘藍'),('bok_choy','青江白菜'),('sponge_gourd','絲瓜')]:
            a=self.eval['by_crop'][f'h=7|{crop}'];b=self.eval['by_crop'][f'h=14|{crop}'];rows.append([cn,f"{a['n']:,}／{a['macro_f1']:.4f}",f"{b['n']:,}／{b['macro_f1']:.4f}"])
        self.table(s,.85,2.05,11.6,[3,4.3,4.3],[.7,.89,.89,.89],rows,size=23)
        self.text(s,.87,5.9,11.6,.55,'分數隨品項不同；此處只描述結果，不推定差異原因。',20,tint=ACCENT)
        self.note(s,'附錄A7 分品項',0,'全部使用封存JSON的by_crop，不跨資料排名。市場平均價表現不能當成任何一店的準確度。',['E2'],'同品項時序與市場觀測可能相關，未做顯著性或成因檢定。')

    def p_confusion(self):
        s=self.page('附錄A9｜7天混淆矩陣：上漲容易漏掉','附錄','[E1] 列為實際類別，欄為模型預測類別；n＝2,085')
        d=self.eval['horizons']['h=7']['selected']['direction'];names=['下跌','持平','上漲'];rows=[['實際＼預測',*names]]
        rows += [[names[i],*map(str,row)] for i,row in enumerate(d['confusion_matrix'])]
        self.table(s,.85,2.05,7.45,[2.2,1.75,1.75,1.75],[.76,.88,.88,.88],rows,size=23)
        self.text(s,9,2.15,3.5,.48,'上漲召回',22,bold=True,tint=ACCENT)
        self.text(s,9,2.9,3.5,1.0,'16 ÷ 158\n≈ 10.1%',26,bold=True)
        self.text(s,9,4.4,3.45,1.05,'142筆實際上漲，\n沒有被報為上漲。',19)
        self.note(s,'附錄A8 混淆矩陣',0,'實際上漲一百五十八筆裡，十六筆預測上漲；四十三筆預測下跌、九十九筆預測持平，合計漏報一百四十二筆。',['E1'],'7天RF既有封存測試；類別順序依JSON down/flat/up。')

    def p_refs_impl(self):
        s=self.page('附錄A10｜引用、實作與交付索引','附錄','完整URL與讀取層級見docs/proposal_v5/ARTICLE_SUMMARY_TABLE.md與docs/REFERENCES.md')
        entries=[('[R01] 陳泯宏 2024｜[R02] 李岱鑫 2015｜[R03] 林沂臻 2017','學位論文（摘要實讀）；批發/市場層級預測與私有資料價值。'),('[R04] 大數據平台 2018｜[R05] 白菜即時｜[R06] 農產分析｜[R07] NCHU 2025','官方零售估計（報導）與產品/課程頁面查核；未安裝實測。'),('[R10] 農糧署2026徵件｜[W1] 王鎬杰2010｜[N1] 公視2025-08-13','政策動向；官方災後統計分析；消費端歷史背景新聞。'),('[H17] 同課程Team 17，2025','蔬果價格預測LightGBM採購指南；15頁PDF第一手閱讀11/15頁；僅作者簡報。'),('[Proposal v5 文件包]','PROPOSAL／DEEP_RESEARCH／ARTICLE_SUMMARY_TABLE／AGENT_DESIGN／DESIGN_DELTA（docs/proposal_v5/）。'),('[實作狀態]','/forecast、/agent/query、/records＋ForecastEngine＋AgentTools（get_market_quote、post_forecast）＝本機原型；save_record工具化與LLM後端、SERVER、影片、發布＝Proposed／暫緩。')]
        for i,(head,body) in enumerate(entries):
            y=1.75+i*.82;self.text(s,.82,y,11.68,.33,head,16,bold=True,tint=ACCENT);self.text(s,.82,y+.37,11.68,.52,body,14,tint=MUTED,linespace=1.1)
        self.note(s,'附錄A9 引用與實作索引',0,'引用以已讀證據為限；摘要未載明的功能不視為不存在。實作與暫緩分列，不把文件完成寫成產品驗收。影片未錄、GitHub/YouTube/課程提交未發布。',['G1','AD1','DD1','P1'],'本版不覆寫README/TASKS/AGENTS/OpenSpec正式狀態；ChatGPT獨立複審另行記錄。')

    def build(self):
        self.p_cover();self.p_motivation();self.p_related();self.p_products_gap();self.p_summary_main()
        self.p_rq();self.p_mindsets();self.p_controversies();self.p_questions()
        self.p_agent_principles();self.p_architecture();self.p_flowchart();self.p_pseudocode()
        self.p_data();self.p_target();self.p_a_mode();self.p_b_mode();self.p_selection()
        self.p_direction();self.p_mae_recall();self.p_ui();self.p_plan();self.p_conclusion()
        self.p_sum_full_1();self.p_sum_full_2();self.p_sum_full_3();self.p_ten_questions();self.p_algo_full()
        self.p_purge();self.p_formulas();self.p_by_crop();self.p_confusion();self.p_refs_impl()
        assert len(self.prs.slides)==33 and len(self.notes)==33

    def save(self):
        self.out.mkdir(parents=True,exist_ok=True);ppt=self.out/(NAME+'.pptx')
        if ppt.exists():raise FileExistsError(ppt)
        self.prs.save(str(ppt));temp=ppt.with_suffix('.tmp')
        with zipfile.ZipFile(ppt) as zin,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as zout:
            for n in sorted(zin.namelist()):
                zi=zipfile.ZipInfo(n,date_time=(2026,10,8,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED;zout.writestr(zi,zin.read(n))
        temp.replace(ppt)
        main=[r for r in self.notes if r['kind']=='主講'];total=sum(r['seconds'] for r in main)
        records={'version':VERSION,'title':self.prs.core_properties.title,'main_slides':len(main),'appendix_slides':len(self.notes)-len(main),'estimated_main_seconds':total,'time_note':'講解設計估時，不是實際配音或錄影長度。','slides':self.notes}
        (self.out/'notes_v5.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
        lines=['# TW01 Proposal v5 逐頁講稿','',f'配套：{NAME}.pptx；{len(main)}頁主講＋{len(self.notes)-len(main)}頁附錄。',f'主講設計估時：{total//60}分{total%60:02d}秒；尚未配音或錄製。','','PPT備註與本檔同源；詳細引用見每頁備註與SOURCES.md。','']
        for r in self.notes:
            lines.extend([f"## {r['kind']} 第{r['page']}頁｜{r['title']}",'',r['script'],'','**補充／證據邊界**：'+r['extra'],'','**來源**：'+'、'.join('['+x+']' for x in r['source_ids']),''])
        (self.out/'SLIDE_NOTES_v5.md').write_text('\n'.join(lines),encoding='utf-8')
        (self.out/'SOURCES.md').write_text('# TW01 Proposal v5 來源定位\n\n'+'\n\n'.join(f'## [{k}]\n{v}' for k,v in SOURCES.items()),encoding='utf-8')
        (self.evidence/'layout_manifest.json').write_text(json.dumps(self.layout,ensure_ascii=False,indent=2),encoding='utf-8')
        inputs=['outputs/evaluation/public/public_test_results.json','outputs/proposal_delivery/run3_20261004_01/stats_master.json','outputs/e2e/ui_ab_mobile_390x844.png']
        (self.evidence/'build_manifest.json').write_text(json.dumps({'version':VERSION,'pptx':str(ppt),'slides':33,'main':23,'appendix':10,'seconds_estimated_main':total,'source_sha256':{p:sha(self.root/p) for p in inputs},'pptx_sha256':sha(ppt),'style':'v4 white style extended: deep research, article summary, agent design (architecture/flowchart/pseudocode) with CURRENT/PARTIAL/PROPOSED boundary','limits':'No model inference/training, product code changes, animation, video, publishing or independent acceptance.'},ensure_ascii=False,indent=2),encoding='utf-8')
        return ppt

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--evidence',type=Path,required=True)
    a=ap.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    d=Deck(a.root.resolve(),a.out.resolve(),a.evidence.resolve());d.build();p=d.save()
    print(json.dumps({'pptx':str(p),'pages':len(d.prs.slides),'notes':len(d.notes),'estimated_main_seconds':sum(r['seconds'] for r in d.notes if r['kind']=='主講')},ensure_ascii=False))

if __name__=='__main__':main()
