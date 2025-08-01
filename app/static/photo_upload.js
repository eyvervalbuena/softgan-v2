document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.photo-box').forEach(box => {
    const input = box.parentElement.querySelector('input[type="file"]');
    if (!input) return;

    // hide input if not already hidden
    input.classList.add('d-none');

    const placeholder = box.innerHTML;

    box.addEventListener('click', () => input.click());

    input.addEventListener('change', () => {
      const file = input.files && input.files[0];
      if (!file) {
        box.innerHTML = placeholder;
        box.classList.add('text-muted');
        return;
      }
      const reader = new FileReader();
      reader.onload = e => {
        const img = new Image();
        img.src = e.target.result;
        box.innerHTML = '';
        box.appendChild(img);
        box.classList.remove('text-muted');
      };
      reader.readAsDataURL(file);
    });
  });
});