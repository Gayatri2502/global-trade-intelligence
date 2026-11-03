"""Bounded public-business discovery. Standard library only; no login bypass."""
import argparse, hashlib, hmac, ipaddress, json, os, re, socket, time, uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib import request, parse, robotparser, error
import xml.etree.ElementTree as ET

AGENT='GlobalTradeResearch/1.0 (+public business contact discovery)'
SOCIAL={'facebook.com','instagram.com','linkedin.com','tiktok.com','x.com','twitter.com','youtube.com'}
class Page(HTMLParser):
 def __init__(self):super().__init__();self.text=[];self.links=[];self.hidden=0;self.title=[];self.in_title=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ('script','style'):self.hidden+=1
  if tag=='title':self.in_title=True
  if tag=='a' and a.get('href'):self.links.append(a['href'])
 def handle_endtag(self,tag):
  if tag in ('script','style'):self.hidden=max(0,self.hidden-1)
  if tag=='title':self.in_title=False
 def handle_data(self,text):
  if not self.hidden:self.text.append(text)
  if self.in_title:self.title.append(text)
def safe_url(url):
 p=parse.urlparse(url)
 if p.scheme!='https' or not p.hostname or p.username or p.password or p.port not in (None,443):raise ValueError('Only public HTTPS sources are allowed')
 addresses=socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM)
 if any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):raise ValueError('Non-public address rejected')
 return p
class SafeRedirect(request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):safe_url(newurl);return super().redirect_request(req,fp,code,msg,headers,newurl)
def fetch(url,token=None):
 safe_url(url)
 headers={'User-Agent':AGENT}
 if token:headers['Authorization']='Bearer '+token
 opener=request.build_opener(SafeRedirect)
 with opener.open(request.Request(url,headers=headers),timeout=15) as response:
  if response.status!=200:raise ValueError('HTTP '+str(response.status))
  data=response.read(1500001)
  if len(data)>1500000:raise ValueError('Response too large')
  return data.decode('utf-8','replace')
def permitted(url,cache):
 p=safe_url(url);origin='https://'+p.netloc
 if origin not in cache:
  rp=robotparser.RobotFileParser();rp.set_url(origin+'/robots.txt')
  try:rp.parse(fetch(origin+'/robots.txt').splitlines());cache[origin]=rp
  except error.HTTPError as exc:
   if exc.code==404:cache[origin]=True
   else:cache[origin]=False
  except Exception:cache[origin]=False
 policy=cache[origin]
 return policy if isinstance(policy,bool) else policy.can_fetch(AGENT,url)
def canonical(url):
 p=parse.urlparse(url);return parse.urlunparse((p.scheme,p.netloc.lower(),p.path.rstrip('/') or '/','','',''))
def public_phones(text, links):
 """Extract explicitly published phone channels, avoiding unlabeled numeric IDs."""
 candidates = [parse.unquote(link[4:]) for link in links if link.lower().startswith('tel:')]
 for link in links:
  url = parse.urlparse(link)
  if url.scheme == 'https' and url.hostname == 'wa.me':
   candidates.append('+' + url.path.strip('/'))
 candidates.extend(re.findall(
  r'(?:phone|telephone|mobile|whatsapp|call us|tel)\s*(?:no\.?|number)?\s*[:：]?\s*(\+?\d[\d(). \t-]{7,22}\d)',
  text, re.I))
 phones = set()
 for raw in candidates:
  digits = re.sub(r'\D', '', raw)
  if 8 <= len(digits) <= 15 and len(set(digits)) > 2:
   phones.add(('+' if raw.strip().startswith('+') else '') + digits)
 return phones

def extract(url,html,source):
 page=Page();page.feed(html);text=' '.join(page.text);low=text.lower()
 if any(x in low[:5000] for x in ['verify you are human','access denied','just a moment','captcha']):raise ValueError('Block page; not bypassed')
 emails=set(re.findall(r'\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b',text,re.I))
 phones=public_phones(text,page.links);social=[]
 for link in page.links:
  if link.startswith('mailto:'):emails.add(parse.unquote(link[7:].split('?')[0]))
  host=(parse.urlparse(link).hostname or '').removeprefix('www.')
  if host in SOCIAL:social.append(link.split('?')[0])
 # Avoid guessing phone numbers from product quantities, dates or licence IDs.
 product=source.get('product') or next((p for p in ['Moringa','Makhana','Garlic powder','Tomato powder','Exotic fruits','Vanilla'] if p.lower() in low),'Other / review')
 role=source.get('role') or ('Exporter / review' if 'export' in low else 'Importer / review' if 'import' in low else 'Supplier / review')
 company=source.get('company') or ' '.join(page.title).strip()[:200] or parse.urlparse(url).hostname
 if not emails and not phones:return None,page.links
 domain=(parse.urlparse(url).hostname or '').removeprefix('www.')
 lead={'lead_id':hashlib.sha256(domain.encode()).hexdigest()[:32],'company':company,'role':role,'product':product,'country':source.get('country','NA'),'phone':'; '.join(sorted(phones)[:4]) or 'NA','email':'; '.join(sorted(emails)[:4]) or 'NA','website':canonical(url),'social_urls':sorted(set(social))[:15],'evidence':'Public business contact page: '+canonical(url)+'. Collected '+datetime.now(timezone.utc).isoformat()+'. Page claims and role require verification.','status':'Unverified'}
 return lead,page.links
def signed_post(config,payload):
 secret=os.environ['CRAWLER_SIGNING_SECRET'];body=json.dumps(payload,separators=(',',':')).encode();stamp=str(int(time.time()));signature=hmac.new(secret.encode(),stamp.encode()+b'.'+body,hashlib.sha256).hexdigest()
 req=request.Request(config['endpoint'],data=body,method='POST',headers={'Content-Type':'application/json','x-trade-timestamp':stamp,'x-trade-signature':signature})
 with request.urlopen(req,timeout=60) as response:return json.load(response)
def discover(config,summary):
 seeds=list(config['sources']);sources=[]
 # Public search RSS is best effort. No paid provider or search-result scraping bypass.
 for query in config.get('search_queries',[])[:3]:
  try:
   xml=ET.fromstring(fetch('https://www.bing.com/search?format=rss&q='+parse.quote(query)))
   for item in xml.findall('.//item')[:5]:
    url=item.findtext('link') or '';host=(parse.urlparse(url).hostname or '').removeprefix('www.')
    if url.startswith('https://') and host not in SOCIAL:sources.append({'url':url})
  except Exception as exc:summary['errors'].append({'provider':'public_search_rss','reason':type(exc).__name__})
 return seeds[:10]+sources+seeds[10:]
def social_api(config,summary):
 token=os.environ.get('META_ACCESS_TOKEN');version=os.environ.get('META_GRAPH_VERSION')
 if not token or not version:
  summary['social_status']='Not configured: authorized Meta API token, version and targets required';return []
 output=[]
 for page_id in config.get('facebook_page_ids',[])[:10]:
  if not re.fullmatch(r'\d+',str(page_id)):continue
  try:
   fields='name,website,phone,emails,about,location,link'
   record=json.loads(fetch('https://graph.facebook.com/'+version+'/'+str(page_id)+'?fields='+parse.quote(fields),token))
   if record.get('website'):output.append({'url':record['website'].split()[0],'company':record.get('name'),'role':'Business / review'})
  except Exception as exc:summary['errors'].append({'provider':'facebook_api','reason':type(exc).__name__})
 account=os.environ.get('META_IG_BUSINESS_ID')
 for username in config.get('instagram_business_usernames',[])[:10]:
  if not account or not re.fullmatch(r'[A-Za-z0-9._]+',username):continue
  try:
   fields='business_discovery.username('+username+'){name,website,biography,username}'
   record=json.loads(fetch('https://graph.facebook.com/'+version+'/'+account+'?fields='+parse.quote(fields),token)).get('business_discovery',{})
   if record.get('website'):output.append({'url':record['website'],'company':record.get('name'),'role':'Business / review'})
  except Exception as exc:summary['errors'].append({'provider':'instagram_api','reason':type(exc).__name__})
 summary['social_status']='Authorized API targets processed; consult errors for inaccessible targets'
 return output
def run(config):
 summary={'pages_fetched':0,'domains':0,'leads':0,'errors':[]};cache={};leads={};seen_domains=set();deadline=time.monotonic()+420
 sources=discover(config,summary)+social_api(config,summary)
 for source in sources:
  url=source['url'];host=(parse.urlparse(url).hostname or '').removeprefix('www.')
  if not host or host in seen_domains or host in SOCIAL:continue
  if len(seen_domains)>=config['max_domains'] or time.monotonic()>deadline:break
  seen_domains.add(host);queue=[url];seen=set()
  while queue and len(seen)<config['pages_per_domain'] and time.monotonic()<deadline:
   current=queue.pop(0)
   if current in seen:continue
   seen.add(current)
   try:
    if not permitted(current,cache):raise ValueError('robots.txt disallows crawl or could not be checked')
    html=fetch(current);summary['pages_fetched']+=1
    lead,links=extract(current,html,source)
    if lead:
     old=leads.get(lead['lead_id'])
     if old:
      for field in ['email','phone']:
       if old[field]=='NA' and lead[field]!='NA':old[field]=lead[field]
      old['social_urls']=sorted(set(old['social_urls']+lead['social_urls']))
     else:leads[lead['lead_id']]=lead
    for link in links:
     target=canonical(parse.urljoin(current,link));p=parse.urlparse(target)
     if p.scheme=='https' and (p.hostname or '').removeprefix('www.')==host and any(word in p.path.lower() for word in ['contact','about']) and target not in seen:queue.append(target)
   except Exception as exc:summary['errors'].append({'url':current,'reason':str(exc)[:150]})
   time.sleep(config['delay_seconds'])
 summary['domains']=len(seen_domains);summary['leads']=len(leads)
 return list(leads.values()),summary
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--dry-run',action='store_true');args=parser.parse_args()
 config=json.loads(Path(__file__).with_name('config.json').read_text());leads,summary=run(config)
 if not args.dry_run:
  result=signed_post(config,{'kind':'discovery_ingest','spreadsheetId':config['spreadsheet_id'],'run_id':str(uuid.uuid4()),'leads':leads,'summary':summary})
  if not result.get('ok'):raise RuntimeError('Discovery ingest rejected')
 print(json.dumps(summary,indent=2))
