import pygetwindow as gw
import time
 
 
def listar_janelas_abertas() -> None:
    janelas = gw.getAllWindows()
 
    for index, janela in enumerate(janelas, start=1):
        titulo = janela.title.strip()
 
        if titulo:
            print("=" * 40)
            print(f"#{index}")
            print(f"Título : {titulo}")
            print(f"Ativa  : {janela.isActive}")
            print(f"Minim. : {janela.isMinimized}")
            print(f"Posição: x={janela.left}, y={janela.top}")
            print(f"Tamanho: w={janela.width}, h={janela.height}")
 
 
if __name__ == "__main__":
 
    time.sleep(5)
 
    listar_janelas_abertas()