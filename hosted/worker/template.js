const SID='1wNPYCBBXAn3y2uJ4LOV6vGgWzYhro_PPGk2HsU0cjj0';
async function read(env,kind){
 const body=JSON.stringify({kind,spreadsheetId:SID}),timestamp=String(Math.floor(Date.now()/1000));
 const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(env.TRADE_OPERATIONS_SECRET),{name:'HMAC',hash:'SHA-256'},false,['sign']);
 const bytes=await crypto.subtle.sign('HMAC',key,new TextEncoder().encode(timestamp+'.'+body));
 const signature=Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
 const response=await fetch('https://cdnzpncsbxavakbvtgem.supabase.co/functions/v1/trade-sync',{method:'POST',headers:{'Content-Type':'application/json','x-trade-signature':signature,'x-trade-timestamp':timestamp},body});
 if(!response.ok)throw Error('Cloud data unavailable');return response.json();
}
export default {async fetch(request,env){
 const path=new URL(request.url).pathname;const headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'};
 if(request.method!=='GET')return new Response('Method not allowed',{status:405});
 try{
  if(path==='/api/data'){
   const data=await read(env,'dashboard_read');data.model.meta.refreshedAt=data.updatedAt;
   return Response.json(data.model,{headers});
  }
  if(path==='/api/workbook'){
   const data=await read(env,'backup_read'),bytes=Uint8Array.from(atob(data.content.replace(/\s/g,'')),c=>c.charCodeAt(0));
   return new Response(bytes,{headers:{...headers,'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','Content-Disposition':'attachment; filename="Trade_Business_Dashboard.xlsx"'}});
  }
  const asset=path==='/api/map'?'/world.geojson':path;
  if(!(asset in ASSETS))return new Response('Not found',{status:404});
  const type=asset==='/'?'text/html':asset.endsWith('.css')?'text/css':asset.endsWith('.geojson')?'application/json':'text/javascript';
  return new Response(ASSETS[asset],{headers:{...headers,'Content-Type':type+'; charset=utf-8'}});
 }catch{return Response.json({error:'Cloud data unavailable; check the private operations workflow.'},{status:503,headers});}
}};
