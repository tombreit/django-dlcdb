// SPDX-FileCopyrightText: Thomas Breitner
//
// SPDX-License-Identifier: EUPL-1.2

// "Show password" button of the login form (registration/login.html),
// loaded as the media of EmailAuthenticationForm.
const button = document.querySelector('[data-password-toggle]');
const input = document.getElementById(button.getAttribute('aria-controls'));

button.addEventListener('click', () => {
    const reveal = input.type === 'password';
    input.type = reveal ? 'text' : 'password';
    button.setAttribute('aria-pressed', String(reveal));
    button.querySelector('.bi').className = reveal ? 'bi bi-eye-slash' : 'bi bi-eye';
});

// Hide it again on submit: the browser should neither keep a visible password
// in its form history nor show it after navigating back.
input.form.addEventListener('submit', () => {
    input.type = 'password';
});
