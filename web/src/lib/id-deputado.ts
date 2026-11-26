/** Formato aceito para o id de deputado na URL. Fora disso a página responde 404 sem ir à API nem criar cache. */
export const ID_SEGURO = /^[A-Za-z0-9_-]{1,32}$/;

export const idValido = (id: string): boolean => ID_SEGURO.test(id);
