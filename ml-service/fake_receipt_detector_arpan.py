#!/usr/bin/env python3
"""Complete Fake Receipt Detection System - All modules in one file"""
import cv2,numpy as np,json,pytesseract,re
from pathlib import Path
from typing import Dict,List,Tuple,Optional
from scipy import signal,stats
from scipy.signal import find_peaks
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime

class TextQualityAnalyzer:
    def __init__(self,image):self.image=image;self.gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};text=pytesseract.image_to_string(self.gray);ocr=pytesseract.image_to_data(self.gray,output_type=pytesseract.Output.DICT)
        _,b=cv2.threshold(self.gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU);lap=cv2.Laplacian(self.gray,cv2.CV_64F).var();r['details']['sharpness']={'val':float(lap),'sus':lap<50}
        conf=[c for c in ocr['conf']if c!=-1];r['details']['ocr']={'avg':float(np.mean(conf))if conf else 0,'sus':np.mean(conf)<70 if conf else True}
        words=re.findall(r'\b[a-zA-Z]{3,}\b',text.lower());rcpt=['total','tax','item','date','receipt'];match=sum(1 for w in words if w in rcpt)
        r['details']['vocab']={'ratio':match/max(len(words),1),'sus':match/max(len(words),1)<0.1};sus=sum(1 for d in r['details'].values()if d.get('sus'));r['score']=max(0,100-sus*20)
        r['flags']=[f"{k}:issue"for k,v in r['details'].items()if v.get('sus')];return r

class PaperCharacteristicsAnalyzer:
    def __init__(self,image):self.image=image;self.gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};_,b=cv2.threshold(self.gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU);bg=self.gray[b==255]
        ts=np.std(bg)if len(bg)>100 else 0;r['details']['texture']={'std':float(ts),'sus':ts<3 or ts>30}
        edges=cv2.Canny(self.gray,50,150);cnt,_=cv2.findContours(edges,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if cnt:lc=max(cnt,key=cv2.contourArea);p=cv2.arcLength(lc,True);h=cv2.convexHull(lc);hp=cv2.arcLength(h,True);irr=(p-hp)/hp if hp>0 else 0;r['details']['edges']={'irr':float(irr),'sus':irr<0.01}
        else:r['details']['edges']={'irr':0,'sus':True}
        sus=sum(1 for d in r['details'].values()if d.get('sus'));r['score']=max(0,100-sus*25);r['flags']=[f"{k}:issue"for k,v in r['details'].items()if v.get('sus')];return r

class PrintingArtifactsAnalyzer:
    def __init__(self,image):self.image=image;self.gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};edges=cv2.Canny(self.gray,50,150);lines=cv2.HoughLinesP(edges,1,np.pi/180,50,minLineLength=30,maxLineGap=5)
        hc=0
        if lines is not None:
            for ln in lines:x1,y1,x2,y2=ln[0];a=abs(np.arctan2(y2-y1,x2-x1)*180/np.pi);hc+=1 if a<10 or a>170 else 0
        r['details']['hlines']={'cnt':hc,'sus':hc<5};_,bi=cv2.threshold(self.gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU);n,lb,st,_=cv2.connectedComponentsWithStats(bi,8)
        dens=[np.mean(self.gray[lb==i])for i in range(1,n)if 10<st[i,cv2.CC_STAT_AREA]<5000]
        ds=np.std(dens)if dens else 10;r['details']['density']={'std':float(ds),'sus':ds<5 or ds>40};sus=sum(1 for d in r['details'].values()if d.get('sus'))
        r['score']=max(0,100-sus*25);r['flags']=[f"{k}:issue"for k,v in r['details'].items()if v.get('sus')];return r

class VisualConsistencyAnalyzer:
    def __init__(self,image):self.image=image;self.gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};h,w=self.gray.shape;gs=8;ch,cw=h//gs,w//gs;bv=[np.mean(self.gray[i*ch:(i+1)*ch,j*cw:(j+1)*cw])for i in range(gs)for j in range(gs)]
        ba=np.array(bv).reshape(gs,gs);gy,gx=np.gradient(ba);gd=np.arctan2(gy,gx);dst=np.std(gd);r['details']['light']={'std':float(dst),'sus':dst>1.5}
        blur=cv2.GaussianBlur(self.gray,(5,5),0);noise=cv2.absdiff(self.gray,blur);ns=np.std(noise);r['details']['noise']={'std':float(ns),'sus':ns<2 or ns>15}
        sus=sum(1 for d in r['details'].values()if d.get('sus'));r['score']=max(0,100-sus*25);r['flags']=[f"{k}:issue"for k,v in r['details'].items()if v.get('sus')];return r

class GeometricAnalyzer:
    def __init__(self,image):self.image=image;self.gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};edges=cv2.Canny(self.gray,50,150);lines=cv2.HoughLines(edges,1,np.pi/180,100)
        if lines is not None and len(lines)>=4:angles=[l[0][1]*180/np.pi for l in lines];h,_=np.histogram(angles,bins=36,range=(0,180));dom=len(np.where(h>len(lines)*0.1)[0]);r['details']['persp']={'dom':dom,'sus':dom>5}
        else:r['details']['persp']={'dom':0,'sus':False}
        _,bi=cv2.threshold(self.gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU);n,lb,st,_=cv2.connectedComponentsWithStats(bi,8)
        hts=[st[i,cv2.CC_STAT_HEIGHT]for i in range(1,n)if 20<st[i,cv2.CC_STAT_AREA]<5000]
        hcv=(np.std(hts)/np.mean(hts))if hts and np.mean(hts)>0 else 0;r['details']['scale']={'cv':float(hcv),'sus':hcv<0.1 or hcv>0.7}
        sus=sum(1 for d in r['details'].values()if d.get('sus'));r['score']=max(0,100-sus*25);r['flags']=[f"{k}:issue"for k,v in r['details'].items()if v.get('sus')];return r

class AIArtifactDetector:
    def __init__(self,image):self.image=image;self.gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};f=np.fft.fft2(self.gray);fs=np.fft.fftshift(f);mag=np.abs(fs);h,w=mag.shape;cy,cx=h//2,w//2
        re=[];
        for rad in[10,30,50]:m=np.zeros((h,w),np.uint8);cv2.circle(m,(cx,cy),rad,1,-1);re.append(np.mean(mag[m>0]))
        fo=np.mean(np.diff(re))if len(re)>1 else 0;r['details']['freq']={'fall':float(fo),'sus':fo>-1.0};blur=cv2.GaussianBlur(self.gray,(5,5),0)
        noise=cv2.absdiff(self.gray,blur);nm=np.mean(noise);r['details']['noise']={'mean':float(nm),'sus':nm<5 or nm>50}
        sus=sum(1 for d in r['details'].values()if d.get('sus'));r['score']=max(0,100-sus*30);r['flags']=[f"{k}:AI artifact"for k,v in r['details'].items()if v.get('sus')];return r

class MetadataAnalyzer:
    def __init__(self,path):self.path=path
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};
        try:img=Image.open(self.path);exif=img._getexif();has=exif is not None;r['details']['exif']={'has':has,'sus':not has};r['score']=100 if has else 50
        except:r['details']['exif']={'has':False,'sus':True};r['score']=50
        r['flags']=['No EXIF data']if r['details']['exif']['sus']else[];return r

class LogicalConsistencyAnalyzer:
    def __init__(self,image,db_config=None):self.image=image;self.gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY);self.db_config=db_config or{}
    def _check_sequential_numbers(self,text):
        patterns=[r'(?:receipt|rcpt|trans|order|invoice)[#:\s]*(\d{4,})',r'#(\d{6,})',r'(?:no|num)[.:\s]*(\d{4,})'];nums=[]
        for p in patterns:nums.extend(re.findall(p,text.lower()))
        if not nums:return{'found':[],'suspicious':False,'reason':'No receipt numbers found'}
        vals=[int(n)for n in nums];sus_round=any(v%1000==0 for v in vals);sus_seq=False
        if len(vals)>1:diffs=[abs(vals[i+1]-vals[i])for i in range(len(vals)-1)];sus_seq=any(d>10000 for d in diffs)
        sus=sus_round or sus_seq;reason=[]
        if sus_round:reason.append('suspiciously round numbers')
        if sus_seq:reason.append('irregular sequence jumps')
        return{'found':vals,'suspicious':sus,'reason':'; '.join(reason)if reason else'Normal'}
    def _validate_with_db(self,text):
        if not self.db_config.get('enabled'):return{'checked':False,'suspicious':False,'reason':'DB validation disabled'}
        try:
            import requests;api_url=self.db_config.get('api_url','https://api.example.com/validate');api_key=self.db_config.get('api_key','YOUR_API_KEY_HERE')
            rcpt_nums=re.findall(r'\d{6,}',text);business=re.findall(r'^[A-Z][A-Za-z\s&]+',text,re.MULTILINE)
            payload={'receipt_numbers':rcpt_nums[:3],'business_name':business[0]if business else'','api_key':api_key}
            resp=requests.post(api_url,json=payload,timeout=5);
            if resp.status_code==200:data=resp.json();return{'checked':True,'valid':data.get('valid',False),'suspicious':not data.get('valid',False),'reason':data.get('message','')}
            else:return{'checked':False,'suspicious':False,'reason':f'API error: {resp.status_code}'}
        except Exception as e:return{'checked':False,'suspicious':False,'reason':f'DB check failed: {str(e)}'}
    def analyze(self):
        r={'score':0,'flags':[],'details':{}};text=pytesseract.image_to_string(self.gray);dates=re.findall(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',text)
        nums=re.findall(r'\$?\d+\.?\d*',text);amt=[float(n.replace('$',''))for n in nums[:20]if 0.01<=float(n.replace('$','')or 0)<=10000]
        r['details']['dates']={'cnt':len(dates),'sus':len(dates)==0};r['details']['amounts']={'cnt':len(amt),'sus':len(amt)<3}
        kw=['receipt','total','tax','thank'];hkw=any(k in text.lower()for k in kw);r['details']['keywords']={'has':hkw,'sus':not hkw}
        r['details']['sequential']=self._check_sequential_numbers(text);r['details']['db_validation']=self._validate_with_db(text)
        sus=sum(1 for d in r['details'].values()if d.get('sus'));r['score']=max(0,100-sus*15);r['flags']=[f"{k}:{v.get('reason','issue')}"for k,v in r['details'].items()if v.get('sus')];return r

class ReceiptAuthenticityDetector:
    def __init__(self,path,db_config=None):self.path=path;self.image=cv2.imread(path);self.results={};self.db_config=db_config
    def analyze(self):
        self.results['text']=TextQualityAnalyzer(self.image).analyze();self.results['paper']=PaperCharacteristicsAnalyzer(self.image).analyze()
        self.results['print']=PrintingArtifactsAnalyzer(self.image).analyze();self.results['visual']=VisualConsistencyAnalyzer(self.image).analyze()
        self.results['geom']=GeometricAnalyzer(self.image).analyze();self.results['ai']=AIArtifactDetector(self.image).analyze()
        self.results['meta']=MetadataAnalyzer(self.path).analyze();self.results['logic']=LogicalConsistencyAnalyzer(self.image,self.db_config).analyze()
        w={'text':0.2,'paper':0.15,'print':0.15,'visual':0.15,'geom':0.1,'ai':0.15,'meta':0.05,'logic':0.05};sc=sum(self.results[k]['score']*w[k]for k in w);self.results['overall_score']=round(sc,2)
        v='LIKELY AUTHENTIC'if sc>=80 else'POSSIBLY AUTHENTIC'if sc>=60 else'SUSPICIOUS'if sc>=40 else'LIKELY FAKE';self.results['verdict']={'verdict':v,'confidence':'HIGH'if sc>=80 or sc<40 else'MEDIUM','score':sc};return self.results
    def export_report(self,out='report.json'):
        with open(out,'w')as f:json.dump(self.results,f,indent=2)

if __name__=="__main__":
    import sys;
    if len(sys.argv)<2:print("Usage: python fake_receipt_detector.py <image_path>");sys.exit(1)
    det=ReceiptAuthenticityDetector(sys.argv[1]);res=det.analyze();print(f"\nScore: {res['overall_score']}/100");print(f"Verdict: {res['verdict']['verdict']}");det.export_report()
