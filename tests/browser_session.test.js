const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');

const html=fs.readFileSync(path.join(__dirname,'../studio/browser_session/index.html'),'utf8');
const source=html.match(/<script>([\s\S]*)<\/script>/)[1];
function bridge(blocked=false) {
  const messages=[],writes=[],values=new Map();
  let listener;
  const parent={postMessage:(message,origin)=>messages.push({message,origin})};
  const document={referrer:'https://studio.example/app'};
  Object.defineProperty(document,'cookie',{
    get:()=>Array.from(values.entries()).map(([key,value])=>key+'='+value).join('; '),
    set:entry=>{
      if(blocked) throw new Error('Cookies unavailable');
      writes.push(entry);
      const [pair,...attributes]=entry.split('; '),split=pair.indexOf('=');
      const key=pair.slice(0,split),value=pair.slice(split+1);
      if(attributes.includes('Max-Age=0'))values.delete(key);else values.set(key,value);
    }
  });
  const window={addEventListener:(type,handler)=>{listener=handler;}};
  vm.runInNewContext(source,{parent,window,document,location:{origin:'https://studio.example',protocol:'https:'},URL});
  const render=(args,origin='https://studio.example',sender=parent)=>listener({source:sender,origin,data:{type:'streamlit:render',args}});
  return {render,messages,writes,values};
}
const names={group:'spd_example_group',facilitator:'spd_example_facilitator'};

test('remembered access persists only opaque tokens with secure cookie attributes',()=>{
  const b=bridge();
  b.render({names,max_age:2592000,command:{nonce:'1',values:{facilitator:{token:'opaque-admin-token',remember:true}}}});
  assert.match(b.writes[0],/SameSite=Strict/);
  assert.match(b.writes[0],/Secure/);
  assert.match(b.writes[0],/Max-Age=2592000/);
  const reply=b.messages.find(x=>x.message.type==='streamlit:setComponentValue').message.value;
  assert.equal(reply.cookies.facilitator,'opaque-admin-token');
  assert.equal(reply.ack,'1');
  assert.equal(reply.available,true);
});
test('session access and logout do not persist or affect the other role',()=>{
  const b=bridge();
  b.render({names,max_age:100,command:{nonce:'1',values:{group:{token:'group-token',remember:false},facilitator:{token:'admin-token',remember:true}}}});
  assert.doesNotMatch(b.writes[0],/Max-Age=/);
  b.render({names,max_age:100,command:{nonce:'2',values:{facilitator:{token:'',remember:false}}}});
  assert.equal(b.values.get(names.group),'group-token');
  assert.equal(b.values.has(names.facilitator),false);
  assert.match(b.writes.at(-1),/Max-Age=0/);
});
test('foreign messages cannot read or replace access tokens',()=>{
  const b=bridge();
  b.render({names,max_age:100,command:{nonce:'1',values:{group:{token:'foreign',remember:true}}}},'https://attacker.example');
  assert.equal(b.writes.length,0);
  assert.equal(b.messages.filter(x=>x.message.type==='streamlit:setComponentValue').length,0);
});
test('cookie denial is reported and duplicate renders do not create a rerun loop',()=>{
  const b=bridge(true);
  const args={names,max_age:100,command:{nonce:'1',values:{group:{token:'opaque',remember:true}}}};
  b.render(args);
  b.render(args);
  const replies=b.messages.filter(x=>x.message.type==='streamlit:setComponentValue');
  assert.equal(replies.length,1);
  assert.equal(replies[0].message.value.available,false);
});
