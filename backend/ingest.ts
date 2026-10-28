Deno.serve(async (request: Request) => {
  if (request.method !== 'POST') return new Response('Method not allowed', {status: 405});
  const signature = request.headers.get('x-trade-signature');
  const timestamp = request.headers.get('x-trade-timestamp');
  if (!signature || !/^[0-9a-f]{64}$/.test(signature) || !timestamp || !/^\d{10}$/.test(timestamp)) return new Response('Unauthorized', {status: 401});
  if (Math.abs(Date.now()/1000-Number(timestamp))>300) return new Response('Expired request', {status:401});
  const bytes = new Uint8Array(await request.arrayBuffer());
  if(bytes.length>12000000) return new Response('Payload too large',{status:413});
  const body=new TextDecoder().decode(bytes);
  // The administrator key stays inside the Edge Function environment.
  const modern=JSON.parse(Deno.env.get('SUPABASE_SECRET_KEYS') || '{}');
  const key=modern.default || Object.values(modern)[0] || Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  if(!key) return new Response('Backend unavailable',{status:503});
  let parsed;
  try { parsed=JSON.parse(body); } catch { return new Response('Invalid JSON',{status:400}); }
  const discoveryOnly=['discovery_ingest','discovery_ack'].includes(parsed.kind);
  const operations=['snapshot_read','model_upload','dashboard_read','backup_upload','backup_read'].includes(parsed.kind);
  const rpc=operations?'trade_operations':discoveryOnly?'trade_discovery':'trade_ingest';
  const response=await fetch(Deno.env.get('SUPABASE_URL')+'/rest/v1/rpc/'+rpc,{
    method:'POST',headers:{'Content-Type':'application/json','apikey':String(key),'Authorization':'Bearer '+String(key)},
    body:JSON.stringify({p_body:body,p_signature:signature,p_timestamp:Number(timestamp)})
  });
  if(!response.ok) return new Response(JSON.stringify({ok:false,error:'Sync rejected; check IDs, signature and payload'}),{status:400,headers:{'Content-Type':'application/json'}});
  const result=await response.json();
  if(!discoveryOnly && !operations){
    const inbox=await fetch(Deno.env.get('SUPABASE_URL')+'/rest/v1/rpc/trade_discovery',{
      method:'POST',headers:{'Content-Type':'application/json','apikey':String(key),'Authorization':'Bearer '+String(key)},
      body:JSON.stringify({p_body:body,p_signature:signature,p_timestamp:Number(timestamp)})
    });
    if(inbox.ok)result.discovery=(await inbox.json()).discovery;
  }
  return new Response(JSON.stringify(result),{headers:{'Content-Type':'application/json','Cache-Control':'no-store'}});
});
