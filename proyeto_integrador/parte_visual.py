import pygame
import sys

pygame.init()


ANCHO, ALTO = 800, 600
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Simulación de Wave Picking - Warehouse")


ejecutando = True
while ejecutando:
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            ejecutando = False
            
   
    pantalla.fill((255, 255, 255))
    
    pygame.display.flip()

pygame.quit()
sys.exit()