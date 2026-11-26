import { ID_SEGURO } from "./seo";

/** Formato aceito para o id de deputado na URL. Fora disso a página responde 404 sem ir à API nem criar cache. */
export { ID_SEGURO };

export const idValido = (id: string): boolean => ID_SEGURO.test(id);
