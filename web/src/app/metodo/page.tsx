import { rotaDeTexto } from "@/content/rotas-next";

const rota = rotaDeTexto("metodo");

export const generateMetadata = rota.generateMetadata;
export default rota.Pagina;
