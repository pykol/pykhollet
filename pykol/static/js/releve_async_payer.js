function ligne_payer(ev) {
  var req = new XMLHttpRequest();
  var form = ev.target;
  req.open(form.method, form.action, true);
  req.onload = requete_retour;
  req.setRequestHeader('X-CSRFToken', document.getElementsByName('csrfmiddlewaretoken')[0].value);
  req.pykol_origin_form = form;
  req.send(null);
  ev.preventDefault();
}

function requete_retour() {
  var form_parent = this.pykol_origin_form.parentNode;
  form_parent.removeChild(this.pykol_origin_form);
  var ligne = form_parent.parentNode;
  var etat = ligne.querySelector('.ligne-etat');
  etat.textContent = 'Payé';
}

window.addEventListener('load', function(ev) {
  var forms = document.querySelectorAll('table.releve-lignes form');
  for(var i = 0; i < forms.length; i++) {
    forms[i].addEventListener('submit', ligne_payer);
  }
});
