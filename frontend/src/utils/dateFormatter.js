export function formatStreakDate(dateObjOrString) {
  if (!dateObjOrString) return '';
  const date = new Date(dateObjOrString);
  if (isNaN(date.getTime())) return String(dateObjOrString);
  
  const day = date.getDate();
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];
  const month = months[date.getMonth()];
  const yearShort = String(date.getFullYear()).slice(-2);
  
  return `${day} ${month}'${yearShort}`;
}
