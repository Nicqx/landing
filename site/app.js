'use strict';
const allowed = new Set(['/sumplete/', '/tic-tac-toe/', '/chess/']);
document.querySelectorAll('form[data-base]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const code = new FormData(form).get('code').trim();
    if (!allowed.has(form.dataset.base) || !/^[0-9]{5}$/.test(code)) {
      document.getElementById('notice').textContent = 'A szobakód pontosan öt számjegyből áll.';
      return;
    }
    window.location.assign(form.dataset.base + encodeURIComponent(code));
  });
});
