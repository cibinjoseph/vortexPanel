#!/usr/bin/python3

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd


class Panels:
    # a panel object is used to keep track of parameters associated with each panel
    def __init__(self, coords):
        self.xcoords = coords[0]
        self.ycoords = coords[1]
        self.controlPoint = (np.median(self.xcoords), np.median(self.ycoords))
        self.phi = np.arctan2(self.ycoords[-1] - self.ycoords[0],
                              self.xcoords[-1] - self.xcoords[0])
        self.s = np.sqrt((self.ycoords[-1] - self.ycoords[0])**2 +
                         (self.xcoords[-1] - self.xcoords[0])**2)

    def flipCoords(self):
        self.xcoords = np.flip(self.xcoords)
        self.ycoords = np.flip(self.ycoords)
        self.phi = np.arctan2(self.ycoords[-1] - self.ycoords[0],
                              self.xcoords[-1] - self.xcoords[0])


def draw_panel(x1, y1, x2, y2, step):
    #Draws a straight line between two points
    # returns the x and y coordinates for a panel
    m = (y2 - y1) / (x2 - x1)
    b = y1 - m * x1
    xcoord = np.arange(x1, x2, step)
    ycoord = m * xcoord + b
    # plt.plot(xcoord, ycoord)
    return (xcoord, ycoord)


def split_into_panels(x, y, step, numPoints, smallPanel, largePanel):
    firstThird = int(0.33 * numPoints)
    secondThird = int(0.66 * numPoints)
    panel_list = []
    # splits airfoil into pairs of x and y coordinates representing each panel
    lastx = 0
    lasty = 0
    for xcoord, ycoord in zip(x[smallPanel:firstThird][::smallPanel],
                              y[smallPanel:firstThird][::smallPanel]):
        panel_list.append(
            Panels(draw_panel(lastx, lasty, xcoord, ycoord, step)))
        lastx = xcoord
        lasty = ycoord
    for xcoord, ycoord in zip(x[firstThird:secondThird][::largePanel],
                              y[firstThird:secondThird][::largePanel]):
        panel_list.append(
            Panels(draw_panel(lastx, lasty, xcoord, ycoord, step)))
        lastx = xcoord
        lasty = ycoord
    for xcoord, ycoord in zip(x[secondThird:numPoints][::smallPanel],
                              y[secondThird:numPoints][::smallPanel]):
        panel_list.append(
            Panels(draw_panel(lastx, lasty, xcoord, ycoord, step)))
        lastx = xcoord
        lasty = ycoord


# account for the last two panels
    panel_list.append(Panels(draw_panel(lastx, lasty, x[-1], 0, step)))
    return (panel_list)


def findJ(paneli, panelj):
    # this is straightforward math as described in the panel method
    xi = paneli.controlPoint[0]
    yi = paneli.controlPoint[1]
    xj = panelj.xcoords[0]
    yj = panelj.ycoords[0]
    sj = panelj.s
    phii = paneli.phi
    phij = panelj.phi

    A = -(xi - xj) * np.cos(phij) - (yi - yj) * np.sin(phij)
    B = (xi - xj)**2 + (yi - yj)**2
    C = -np.cos(phii - phij)
    D = (xi - xj) * np.cos(phii) + (yi - yj) * np.sin(phii)
    E = np.sqrt(B - A**2)
    J = C / 2 * np.log(
        (sj**2 + 2 * A * sj + B) /
        B) + (D - A * C) / E * (np.arctan2(sj + A, E) - np.arctan2(A, E))
    return (J)


def findJMatrix(listOfPanels, lastPanelIndex):
    # initialize empty matrices so we dont have to append a matrix every iteration
    JMatrix = np.empty([len(listOfPanels), len(listOfPanels)])
    for i, paneli in enumerate(listOfPanels):
        for j, panelj in enumerate(listOfPanels):
            if paneli == panelj:
                # the diagonal of the matrix with all the J values is equal to 0
                # JMatrix[i, j] = np.pi
                JMatrix[i, j] = 0
            else:
                JMatrix[i, j] = findJ(paneli, panelj)

    return (JMatrix)


def findLift(listOfPanels, freestream, alpha, lastPanelIndex, c, JMatrix):
    # initialize empty matrices so we dont have to append a matrix every iteration
    RHSMatrix = np.empty(len(listOfPanels))
    for i, paneli in enumerate(listOfPanels):
        RHSMatrix[i] = -freestream * 2 * np.pi * np.sin(paneli.phi - alpha)

    # need to remove one row in the matrix and then impose kutta condition
    removed_row = len(listOfPanels) - 15
    JMatrix = np.delete(JMatrix, removed_row, 0)
    RHSMatrix = np.delete(RHSMatrix, removed_row, 0)

    new_row = np.zeros(len(listOfPanels))
    new_row[lastPanelIndex] = 1
    new_row[-1] = 1
    JMatrix = np.vstack([JMatrix, new_row])
    RHSMatrix = np.append(RHSMatrix, 0)

    X = np.linalg.solve(JMatrix, RHSMatrix)
    lift = 0
    for i, panel in enumerate(listOfPanels):
        lift = lift + X[i] * panel.s * 2 / (freestream * c)

    return (lift)

def simulate(MPXX='1234', numPoints=7000, showPlots=False):
# Required inputs, airfoil number and chord length
    c = 1

    m = int(MPXX[0])/100
    p = int(MPXX[1])/10
    t = int(MPXX[2:4])/100

    x = np.linspace(0, c, numPoints)

    smallPanel = 25
    largePanel = 50

    if t > 0.0:
        yt = 5 * t * (0.2969 * np.sqrt(x / c) - 0.126 * (x / c) - 0.3516 *
                      (x / c)**2 + 0.2843 * (x / c)**3 - 0.1015 * (x / c)**4)
    else:
        yt = np.zeros(numPoints)

    yc = np.piecewise(x, [x <= p * c, x > p * c], [
        lambda x: m / p**2 * (2 * p * (x / c) - (x / c)**2), lambda x: m /
        (1 - p)**2 * ((1 - 2 * p) + 2 * p * (x / c) - (x / c)**2)
    ])

    dyc = np.piecewise(x, [x <= p * c, x > p * c], [
        lambda x: 2 * m / p**2 * (p - (x / c)), lambda x: 2 * m / (1 - p)**2 *
        (p - (x / c))
    ])

    theta = np.arctan(dyc)

    xu = x - yt * np.sin(theta)
    xl = x + yt * np.sin(theta)

    yu = yc + yt * np.cos(theta)
    yl = yc - yt * np.cos(theta)

    fig1 = plt.figure()
    botPanels = split_into_panels(xl, yl, c / numPoints, numPoints, \
                                  smallPanel, largePanel)
    for panel in botPanels:
        panel.flipCoords()
    topPanels = split_into_panels(xu, yu, c / numPoints, numPoints, \
                                  smallPanel, largePanel)
    listOfPanels = topPanels + botPanels

    freestream = 1
    alpha_max = 15
    alpha_deg = np.linspace(-alpha_max, alpha_max, 2)
    alpha = alpha_deg * np.pi / 180
    cl = np.empty(len(alpha))
    lastPanelIndex = len(topPanels) - 1
    JMatrix = findJMatrix(listOfPanels, lastPanelIndex)
    for i, alf in enumerate(alpha):
        cl[i] = findLift(listOfPanels, freestream, alf, lastPanelIndex, c, JMatrix)

    cl0 = findLift(listOfPanels, freestream, 0.0, lastPanelIndex, c, JMatrix)
    cla = (cl[0]-cl0)/(alpha[0])
    alpha0 = -cl0/cla

    print('NACA ' + MPXX)
    print('CL0           = ' + str(cl0))
    print('CLa (deg-1 ; rad-1) = ' + str(cla*np.pi/180) + ' ; ' + str(cla))
    print('al0 (deg   ; rad  ) = ' + str(alpha0*180/np.pi) + ' ; ' + str(alpha0))

    fig1
    plt.plot(xu, yu, 'g')
    plt.plot(xl, yl, 'g')
# for panel in listOfPanels:
# plt.plot(panel.controlPoint[0], panel.controlPoint[1], '.k')
    plt.xlim(-0.1, c + 0.1)
    plt.ylim(-c / 1.5, c / 1.5)
    plt.title('NACA ' + MPXX + ' Airfoil')
    plt.grid()
    plt.xlabel("x/c")
    plt.ylabel("t/c")
# plt.savefig('./Plots/airfoil.png', dpi=300)

    fig2 = plt.figure()
    plt.grid()
    plt.plot(alpha_deg, cl, '-r')
    plt.title('NACA ' + MPXX + ' Airfoil Cl vs Angle of Attack')
    plt.xlabel('Angle of Attack (\u00b0)')
    plt.ylabel('Cl')
    plt.xlim([-alpha_max, alpha_max])


    airfoil_data = pd.read_csv('./XfoilData/xfoil_data_50000.csv', sep=',')
    airfoil_angle = airfoil_data.values[:, 0]
    airfoil_cl = airfoil_data.values[:, 1]
    plt.plot(airfoil_angle, airfoil_cl, linewidth=1)

    airfoil_data = pd.read_csv('./XfoilData/xfoil_data_100000.csv', sep=',')
    airfoil_angle = airfoil_data.values[:, 0]
    airfoil_cl = airfoil_data.values[:, 1]
    plt.plot(airfoil_angle, airfoil_cl, linewidth=1)

    airfoil_data = pd.read_csv('./XfoilData/xfoil_data_500000.csv', sep=',')
    airfoil_angle = airfoil_data.values[:, 0]
    airfoil_cl = airfoil_data.values[:, 1]
    plt.plot(airfoil_angle, airfoil_cl, linewidth=1)
    plt.xlim(-20, 20)
    plt.legend([
        'Panel Method', 'Xfoil Re = 50,000', 'Xfoil Re = 100,000',
        'Xfoil Re = 500,000'
    ])
# plt.savefig('./Plots/cl_result.png', dpi=300)

# plt.show()

if __name__ == '__main__':
    simulate(MPXX='5605')
