import u from './Util';
import TextConfirm from  './utils/TextConfirm';

u.sub('.revoke-mod2inv', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/revoke_mod2inv/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('#accept-mod2-inv', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/accept_modinv/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('#refuse-mod2-inv', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/refuse_mod2inv/'+nsub, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('.revoke-mod2', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  TextConfirm(this, function(){
    u.post('/do/remove_mod2/'+nsub+'/'+user, {},
    function(data){
      if (data.status == "ok") {
        if(!data.resign){
          document.location.reload();
        }else{
          document.location = '/s/' + nsub;
        }
      }
    });
  });
});

u.sub('.revoke-ban', 'click', function(e){
  var user=this.getAttribute('data-user');
  var nsub=this.getAttribute('data-sub');
  u.post('/do/remove_sub_ban/'+nsub+'/'+user, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

u.sub('#ptoggle', 'click', function(e){
  var oval = document.getElementById('ptypeval').value;
  document.getElementById('ptypeval').value = (document.getElementById('ptypeval').value == 'text') ? 'link' : 'text' ;
  var val = document.getElementById('ptypeval').value;
  this.innerHTML = 'Change to ' + oval + ' post';
  document.getElementById('ptype').innerHTML = val;
  if(val=='text'){
    if(document.getElementById('link').getAttribute('required') === ''){
      window.rReq = true;
      document.getElementById('link').removeAttribute('required');
    }
    u.each('.lncont', function(e){e.style.display='none';});
    u.each('.txcont', function(e){e.style.display=(e.type == "button") ? 'inline-block' : 'block';});
  }else{
    if(window.rReq){
      document.getElementById('link').setAttribute('required', true);
    }
    u.each('.lncont', function(e){e.style.display=(e.type == "button") ? 'inline-block' : 'block';});
    u.each('.txcont', function(e){e.style.display='none';});
  }
});

u.sub('button.blk,button.unblk,button.sub,button.unsub', 'click', function(e){
  var sid=this.parentNode.getAttribute('data-sid');
  var act=this.getAttribute('data-ac')
  u.post('/do/' + act + '/' + sid, {},
  function(data){
    if (data.status == "ok") {
      document.location.reload();
    }
  });
});

window.onkeydown = function(e){
  if(!document.getElementsByClassName('alldaposts')[0]){return;}
  if(e.shiftKey == true && e.which == 88){
    console.log('weew')
    window.expandall = true;
    u.each('div.post', function(t, i){
      var q = t.getElementsByClassName('expando-btn')[0]
      if(q && q.getAttribute('data-icon') == "image"){
        q.click()
      }
    });
  }
}


u.sub('#ban_expires', 'input', function(e){
  var dtime = new Date(new Date(document.getElementById('ban_expires').value).toUTCString().substr(0, 25)).getTime()/1000;
  document.getElementById('ban_expires_data').value = dtime;
});

u.sub('#ban_timepick', 'change', function(e){
  document.getElementById('ban_expires').value = '';
  document.getElementById('ban_expires_data').value = '';
  if(this.value == 'ban_temp'){
    document.getElementById('ban_expires').style.display = 'inline-block';
  }else{
    document.getElementById('ban_expires').style.display = 'none';
  }
  console.log('timepick chnage', this.value)
});