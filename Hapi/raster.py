# -*- coding: utf-8 -*-
"""
GISpy contains python functions to handle raster data align them together
based on a source raster, perform any algebric operation on cell's values

@author: Mostafa
"""

#%library
import os
import re
import sys
import datetime as dt
import numpy as np
import json
import gdal
import osr
import pandas as pd
import geopandas as gpd
from osgeo import gdalconst
# from gdalconst import GA_ReadOnly

import zipfile
import pyproj
import rasterio
import rasterio.merge
import rasterio.mask
import netCDF4

# import datetime as dt
import time

from Hapi.vector import Vector
#import skimage.transform as transform

# import subprocess
# import tarfile
import gzip
import scipy.misc as misc
from osgeo import ogr
# import glob
import scipy.interpolate
from pyproj import Proj, transform


class Raster():
    """
    ==========================================
         Raster
    ==========================================
    Raster class contains methods to deal with rasters and netcdf files,
    change projection and coordinate systems.

    Methods:
        1-GetMask
        2-AddMask
        3-GetTargets
        4-SaveRaster
        5-GetRasterData
        6-MapAlgebra
        7-RasterFill
        8-ResampleRaster
        9-ProjectRaster
        10-ReprojectDataset
        11-RasterLike
        12-MatchNoDataValue
        13-ChangeNoDataValue
        14-MatchRasterAlignment
        15-NearestNeighbour
        16-ReadASCII
        17-StringSpace
        18-WriteASCII
        19-ASCIItoRaster
        20-ClipRasterWithPolygon
        21-Clip2
        22-ClipRasterWithRaster
        23-Mosaic
        24-ReadASCIIsFolder
        25-ASCIIFoldertoRaster
        26-RastersLike
        27-MatchDataAlignment
        28-MatchDataNoValuecells
        29-FolderCalculator
        30-ReadRastersFolder
        31-ExtractValues
        32-OverlayMap
        33-OverlayMaps
        34-Normalize
        35-GetEpsg
        36-NCdetails
        37-NCtoTiff
        38-Convert_nc_to_tiff
        39-Convert_grb2_to_nc
        40-Convert_adf_to_tiff
        41-Convert_bil_to_tiff
        42-Convert_hdf5_to_tiff
        45-SaveNC
        46-Create_NC_name
        47-Create_new_NC_file
        48-Add_NC_Array_Variable
        49-Add_NC_Array_Static
        50-Convert_dict_to_array
        51-Open_array_info
        53-Open_nc_info
        54-Open_nc_array
        55-Open_bil_array
        56-Open_ncs_array
        57-Open_nc_dict
        58-Clip_Dataset_GDAL
        59-clip_data
        60-reproject_dataset_epsg
        61-reproject_MODIS
        62-reproject_dataset_example
        63-resize_array_example
        64-Get_epsg
        65-gap_filling
        66-Vector_to_Raster
        67-Moving_average
        68-Get_ordinal
        69-ListAttributes


    """
    def __init__(self):
        pass

    @staticmethod
    def GetMask(raster):
        """
        =======================================================================
           get_mask(dem)
        =======================================================================

        to create a mask by knowing the stored value inside novalue cells

        Inputs:
        ----------
            1- flow path lenth raster

        Outputs:
        ----------
            1- mask:array with all the values in the flow path length raster
            2- no_val: value stored in novalue cells
        """
        no_val = np.float32(raster.GetRasterBand(1).GetNoDataValue()) # get the value stores in novalue cells
        mask = raster.ReadAsArray()
        return mask, no_val

    @staticmethod
    def AddMask(var, dem=None, mask=None, no_val=None):
        """
        ===================================================================
             add_mask(var, dem=None, mask=None, no_val=None)
        ===================================================================
        Put a mask in the spatially distributed values

        Inputs
        ----------
            1- var : nd_array
                Matrix with values to be masked
            2-cut_dem : gdal_dataset
                Instance of the gdal raster of the catchment to be cutted with. DEM
                overrides the mask_vals and no_val
            3-mask_vals : nd_array
                Mask with the no_val data
            4-no_val : float
                value to be defined as no_val. Will mask anything is not this value

        Outputs
        -------
            1-var : nd_array
                Array with masked values
        """

        if dem != None:
            mask, no_val = Raster.GetMask(dem)

        # Replace the no_data value
        assert var.shape == mask.shape, 'Mask and data do not have the same shape'
        var[mask == no_val] = no_val

        return var

    @staticmethod
    def GetTargets(dem):
        """
        ===================================================================
            get_targets(dem)
        ===================================================================
        Returns the centres of the interpolation targets

        Parameters
        ----------
        dem : gdal_Dataset
            Get the data from the gdal datasetof the DEM

        Returns
        -------

        coords : nd_array [nxm - nan, 2]
            Array with a list of the coordinates to be interpolated, without the Nan

        mat_range : nd_array [n, m]
            Array with all the centres of cells in the domain of the DEM (rectangular)

        """
        # Getting data for the whole grid
        x_init, xx_span, xy_span, y_init, yy_span, yx_span = dem.GetGeoTransform()
        shape_dem = dem.ReadAsArray().shape

        # Getting data of the mask
        no_val = dem.GetRasterBand(1).GetNoDataValue()
        mask = dem.ReadAsArray()

        # Adding 0.5 to get the centre
        x = np.array([x_init + xx_span*(i+0.5) for i in range(shape_dem[0])])
        y = np.array([y_init + yy_span*(i+0.5) for i in range(shape_dem[1])])
        #mat_range = np.array([[(xi, yi) for xi in x] for yi in y])
        mat_range = [[(xi, yi) for xi in x] for yi in y]

        # applying the mask
        coords = []
        for i in range(len(x)):
            for j in range(len(y)):
                if mask[j, i] != no_val:
                    coords.append(mat_range[j][i])
                    #mat_range[j, i, :] = [np.nan, np.nan]

        return np.array(coords), np.array(mat_range)


    @staticmethod
    def SaveRaster(raster,path):
        """
        ===================================================================
          SaveRaster(raster,path)
        ===================================================================
        this function saves a raster to a path

        inputs:
        ----------
            1- raster:
                [gdal object]
            2- path:
                [string] a path includng the name of the raster and extention like
                path="data/cropped.tif"

        Outputs:
        ----------
            the function does not return and data but only save the raster to the hard drive

        EX:
        ----------
            SaveRaster(raster,output_path)
        """
        # input data validation
        # data type
        assert type(raster)==gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(path)== str, "Raster_path input should be string type"
        # input values
        ext=path[-4:]
        assert ext == ".tif", "please add the extension at the end of the path input"

        driver = gdal.GetDriverByName( "GTiff" )
        dst_ds = driver.CreateCopy( path, raster, 0 )
        dst_ds = None # Flush the dataset to disk

    @staticmethod
    def GetRasterData(Input, band=''):
        """
        =====================================================
            GetRasterData(Raster)
        =====================================================
        to create a mask by knowing the stored value inside novalue cells

        Inputs:
        ----------
            Input: [str/gdal.Dataset]
                path to the raster file or a gdal.Dataset
            band : [integer]
                the band you want to get its data. Default is 1
        Outputs:
        ----------
            1- mask:array with all the values in the flow path length raster
            2- no_val: value stored in novalue cells
        """

        if band == '':
            band = 1

        if Input == gdal.Dataset:
            src = Input
        else:
            # if a path is given
            try:
                src = gdal.Open(Input)
            except:
                assert Input != None, Input + ' does not exists'

        # get the value stores in novalue cells
        NoDataValue = np.float32(src.GetRasterBand(band).GetNoDataValue())

        Data = src.GetRasterBand(band).ReadAsArray()

        return Data, NoDataValue

    @staticmethod
    def CreateRaster(Path='', data='', geo='', EPSG='',NoDataValue=-9999):
        """
        =============================================================================
            CreateRaster(Path='', data='', geo='', projection='',NoDataValue=-9999)
        =============================================================================
        CreateRaster method creates a raster from a given array and geotransform data
        and save the figg file if a Path is given or it will return the gdal.Dataset

        Parameters
        ----------
        Path : [str], optional
            Path to save the Raster, if '' is given a memory raster will be returned. The default is ''.
        data : [array], optional
            numpy array. The default is ''.
        geo : [list], optional
            geotransform list [minimum lon, pixelsize, rotation, maximum lat, rotation,
                pixelsize]. The default is ''.
        projection : TYPE, optional
            DESCRIPTION. The default is ''.
        NoDataValue : TYPE, optional
            DESCRIPTION. The default is -9999.

        Returns
        -------
        None.

        """
        if np.isnan(NoDataValue):
            NoDataValue = -9999

        if Path == '':
            driver = gdal.GetDriverByName("MEM")
            dst_ds = driver.Create('', int(data.shape[1]), int(data.shape[0]), 1,
                               gdal.GDT_Float32, ['COMPRESS=LZW'])
        else:
            driver = gdal.GetDriverByName("GTiff")
            dst_ds = driver.Create(Path, int(data.shape[1]), int(data.shape[0]), 1,
                                gdal.GDT_Float32, ['COMPRESS=LZW'])

        srse = osr.SpatialReference()

        if EPSG == '':
            srse.SetWellKnownGeogCS("WGS84")
        else:
            try:
                if not srse.SetWellKnownGeogCS(EPSG) == 6:
                    srse.SetWellKnownGeogCS(EPSG)
                else:
                    try:
                        srse.ImportFromEPSG(int(EPSG))
                    except:
                        srse.ImportFromWkt(EPSG)
            except:
                try:
                    srse.ImportFromEPSG(int(EPSG))
                except:
                    srse.ImportFromWkt(EPSG)

        dst_ds.SetProjection(srse.ExportToWkt())
        dst_ds.GetRasterBand(1).SetNoDataValue(NoDataValue)
        dst_ds.SetGeoTransform(geo)
        dst_ds.GetRasterBand(1).WriteArray(data)

        if Path == '':
            return dst_ds
        else:
            dst_ds = None
            return

    @staticmethod
    def MapAlgebra(src, fun):
        """
        ==============================================================
          MapAlgebra(src, dst, function)
        ==============================================================
        this function executes a mathematical operation on raster array and returns
        the result

        inputs:
        ----------
            1-src:
                [gdal.dataset] source raster to get the location of the NoDataValue and
                where it is in the array
            2-dst:
                [gdal.dataset] source raster to get the location of the NoDataValue and
                where it is in the array
            3-function:
                numpy function

        Example :
        ----------
            A=gdal.Open(evap.tif)
            func=np.abs
            new_raster=MapAlgebra(A,func)
        """
        # input data validation
        # data type
        assert type(src) == gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert callable(fun) , "second argument should be a function"

        src_gt = src.GetGeoTransform()
        src_proj = src.GetProjection()
        src_row = src.RasterYSize
        src_col = src.RasterXSize
        noval = np.float32(src.GetRasterBand(1).GetNoDataValue())
        src_sref = osr.SpatialReference(wkt=src_proj)
        src_array = src.ReadAsArray()

        # fill the new array with the nodata value
        new_array = np.ones((src_row,src_col))*noval
        # execute the function on each cell
        for i in range(src_row):
            for j in range(src_col):
                if src_array[i,j] != noval:
                    new_array[i,j] = fun(src_array[i,j])

        # create the output raster
        mem_drv = gdal.GetDriverByName("MEM")
        dst = mem_drv.Create("",src_col,src_row,1,gdalconst.GDT_Float32) #,['COMPRESS=LZW'] LZW is a lossless compression method achieve the highst compression but with lot of computation

        # set the geotransform
        dst.SetGeoTransform(src_gt)
        # set the projection
        dst.SetProjection(src_sref.ExportToWkt())
        # set the no data value
        dst.GetRasterBand(1).SetNoDataValue(src.GetRasterBand(1).GetNoDataValue())
        # initialize the band with the nodata value instead of 0
        dst.GetRasterBand(1).Fill(src.GetRasterBand(1).GetNoDataValue())
        dst.GetRasterBand(1).WriteArray(new_array)

        return dst

    @staticmethod
    def RasterFill(src, Val, SaveTo):
        """
        ==============================================================
          MapAlgebra(src, dst, function)
        ==============================================================
        this function executes a mathematical operation on raster array and returns
        the result

        inputs:
        ----------
            1-src:
                [gdal.dataset] source raster to get the location of the NoDataValue and
                where it is in the array
            2-dst:
                [gdal.dataset] source raster to get the location of the NoDataValue and
                where it is in the array
            3-function:
                numpy function

        Example :
        ----------
            A=gdal.Open(evap.tif)
            func=np.abs
            new_raster=MapAlgebra(A,func)
        """
        # input data validation
        # data type
        assert type(src)==gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        # assert callable(fun) , "second argument should be a function"

        NoDataVal = src.GetRasterBand(1).GetNoDataValue()
        src_array = src.ReadAsArray()

        if NoDataVal == None:
            NoDataVal = np.nan

        if  not np.isnan(NoDataVal):
            if src_array.dtype == np.float32:
                src_array[src_array != np.float32(NoDataVal)] = Val
            else:
                src_array[src_array != np.float64(NoDataVal)] = Val
        else:
            src_array[~np.isnan(src_array)] = Val

        Raster.RasterLike(src,src_array,SaveTo,pixel_type=1)


    @staticmethod
    def ResampleRaster(src,cell_size,resample_technique="Nearest"):
        """
        ======================================================================
          project_dataset(src, to_epsg):
        ======================================================================
        this function reproject a raster to any projection
        (default the WGS84 web mercator projection, without resampling)
        The function returns a GDAL in-memory file object, where you can ReadAsArray etc.

        inputs:
        ----------
            1- raster:
                gdal dataset (src=gdal.Open("dem.tif"))
            2-to_epsg:
                integer reference number to the new projection (https://epsg.io/)
                (default 3857 the reference no of WGS84 web mercator )
            3-cell_size:
                integer number to resample the raster cell size to a new cell size
                (default empty so raster will not be resampled)
            4- resample_technique:
                [String] resampling technique default is "Nearest"
                https://gisgeography.com/raster-resampling/
                "Nearest" for nearest neighbour,"cubic" for cubic convolution,
                "bilinear" for bilinear

        Outputs:
        ----------
            1-raster:
                gdal dataset (you can read it by ReadAsArray)

        Ex:
        ----------
        projected_raster=project_dataset(src, to_epsg=3857)

        """
        # input data validation
        # data type
        assert type(src)==gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(resample_technique)== str ," please enter correct resample_technique more information see docmentation "

        if resample_technique=="Nearest":
            resample_technique=gdal.GRA_NearestNeighbour
        elif resample_technique=="cubic":
            resample_technique=gdal.GRA_Cubic
        elif resample_technique=="bilinear":
            resample_technique=gdal.GRA_Bilinear

    #    # READ THE RASTER
    #    src = gdal.Open(inputspath+"dem_4km.tif")
        # GET PROJECTION
        src_proj=src.GetProjection()
        # GET THE GEOTRANSFORM
        src_gt=src.GetGeoTransform()
        # GET NUMBER OF columns
        src_x=src.RasterXSize
        # get number of rows
        src_y=src.RasterYSize
        # number of bands
    #    src_bands=src.RasterCount
        # spatial ref
        src_epsg=osr.SpatialReference(wkt=src_proj)

        ulx = src_gt[0]
        uly = src_gt[3]
        # transform the right lower corner point
        lrx = src_gt[0]+src_gt[1]*src_x
        lry = src_gt[3]+src_gt[5]*src_y

        pixel_spacing=cell_size
        # create a new raster
        mem_drv=gdal.GetDriverByName("MEM")
        dst=mem_drv.Create("",int(np.round(abs(lrx-ulx)/pixel_spacing)),int(np.round(abs(uly-lry)/pixel_spacing)),
                           1,gdalconst.GDT_Float32,['COMPRESS=LZW']) # LZW is a lossless compression method achieve the highst compression but with lot of computation

        # set the geotransform
        dst.SetGeoTransform(src_gt)
        # set the projection
        dst.SetProjection(src_epsg.ExportToWkt())
        # set the no data value
        dst.GetRasterBand(1).SetNoDataValue(src.GetRasterBand(1).GetNoDataValue())
        # initialize the band with the nodata value instead of 0
        dst.GetRasterBand(1).Fill(src.GetRasterBand(1).GetNoDataValue())
        # perform the projection & resampling
        gdal.ReprojectImage(src,dst,src_epsg.ExportToWkt(),src_epsg.ExportToWkt(),resample_technique)

        return dst

    @staticmethod
    def ProjectRaster(src, to_epsg,resample_technique="Nearest", Option=2):
        """
        =====================================================================
           project_dataset(src, to_epsg):
        =====================================================================
        this function reproject a raster to any projection
        (default the WGS84 web mercator projection, without resampling)
        The function returns a GDAL in-memory file object, where you can ReadAsArray etc.

        inputs:
        ----------
            1- raster:
                gdal dataset (src=gdal.Open("dem.tif"))
            2-to_epsg:
                integer reference number to the new projection (https://epsg.io/)
                (default 3857 the reference no of WGS84 web mercator )
            3-cell_size:
                integer number to resample the raster cell size to a new cell size
                (default empty so raster will not be resampled)
            4- resample_technique:
                [String] resampling technique default is "Nearest"
                https://gisgeography.com/raster-resampling/
                "Nearest" for nearest neighbour,"cubic" for cubic convolution,
                "bilinear" for bilinear

        Outputs:
        ----------
            1-raster:
                gdal dataset (you can read it by ReadAsArray)

        Ex:
        ----------
            projected_raster=project_dataset(src, to_epsg=3857)
        """
        # input data validation
        # data type
        assert type(src) == gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(to_epsg) == int,"please enter correct integer number for to_epsg more information https://epsg.io/"
        assert type(resample_technique) == str ," please enter correct resample_technique more information see docmentation "

        if resample_technique == "Nearest":
            resample_technique = gdal.GRA_NearestNeighbour
        elif resample_technique == "cubic":
            resample_technique = gdal.GRA_Cubic
        elif resample_technique == "bilinear":
            resample_technique = gdal.GRA_Bilinear

        if Option == 1:
            ### Source raster
            # GET PROJECTION
            src_proj = src.GetProjection()
            # GET THE GEOTRANSFORM
            src_gt = src.GetGeoTransform()
            # GET NUMBER OF columns
            src_x = src.RasterXSize
            # get number of rows
            src_y = src.RasterYSize
            # number of bands
            # src_bands=src.RasterCount
            # spatial ref
            src_epsg = osr.SpatialReference(wkt=src_proj)

            ### distination raster
            # spatial ref
            dst_epsg = osr.SpatialReference()
            dst_epsg.ImportFromEPSG(to_epsg)


            # in case the source crs is GCS and longitude is in the west hemisphere gdal
            # reads longitude fron 0 to 360 and transformation factor wont work with values
            # greater than 180
            if src_epsg.GetAttrValue('AUTHORITY',1) != str(to_epsg) :
                if src_epsg.GetAttrValue('AUTHORITY',1)=="4326" and src_gt[0] > 180:
                    lng_new=src_gt[0]-360
                    # transformation factors
                    tx = osr.CoordinateTransformation(src_epsg,dst_epsg)
                    # transform the right upper corner point
                    (ulx,uly,ulz) = tx.TransformPoint(lng_new, src_gt[3])
                    # transform the right lower corner point
                    (lrx,lry,lrz)=tx.TransformPoint(lng_new+src_gt[1]*src_x,
                                                    src_gt[3]+src_gt[5]*src_y)
                else:
                    xs = [src_gt[0], src_gt[0]+src_gt[1]*src_x]
                    ys = [src_gt[3], src_gt[3]+src_gt[5]*src_y]

                    [uly,lry] , [ulx,lrx] = Vector.ReprojectPoints(ys,xs,from_epsg=int(src_epsg.GetAttrValue('AUTHORITY',1)),
                                                   to_epsg=int(dst_epsg.GetAttrValue('AUTHORITY',1)))


            else:
                ulx = src_gt[0]
                uly = src_gt[3]
                lrx = src_gt[0]+src_gt[1]*src_x
                lry = src_gt[3]+src_gt[5]*src_y

            # get the cell size in the source raster and convert it to the new crs
            # x coordinates or longitudes
            xs = [src_gt[0], src_gt[0] + src_gt[1]]
            # y coordinates or latitudes
            ys = [src_gt[3],src_gt[3]]

            if src_epsg.GetAttrValue('AUTHORITY',1) != str(to_epsg):
                # transform the two points coordinates to the new crs to calculate the new cell size
                new_ys, new_xs = Vector.ReprojectPoints(ys,xs,from_epsg=int(src_epsg.GetAttrValue('AUTHORITY',1)),
                                                  to_epsg=int(dst_epsg.GetAttrValue('AUTHORITY',1)),precision=6)
                # new_xs, new_ys= Vector.ReprojectPoints_2(ys,xs,from_epsg=int(src_epsg.GetAttrValue('AUTHORITY',1)),
                #                                  to_epsg=int(dst_epsg.GetAttrValue('AUTHORITY',1)))
            else:
                new_xs = xs
                new_ys = ys

            pixel_spacing = np.abs(new_xs[0] - new_xs[1])

            # create a new raster
            mem_drv = gdal.GetDriverByName("MEM")
            dst = mem_drv.Create("",int(np.round(abs(lrx-ulx)/pixel_spacing)),int(np.round(abs(uly-lry)/pixel_spacing)),
                               1,gdalconst.GDT_Float32) #['COMPRESS=LZW'] LZW is a lossless compression method achieve the highst compression but with lot of computation

            # new geotransform
            new_geo = (ulx, pixel_spacing, src_gt[2], uly, src_gt[4], np.sign(src_gt[-1])*pixel_spacing)
            # set the geotransform
            dst.SetGeoTransform(new_geo)
            # set the projection
            dst.SetProjection(dst_epsg.ExportToWkt())
            # set the no data value
            dst.GetRasterBand(1).SetNoDataValue(src.GetRasterBand(1).GetNoDataValue())
            # initialize the band with the nodata value instead of 0
            dst.GetRasterBand(1).Fill(src.GetRasterBand(1).GetNoDataValue())
            # perform the projection & resampling
            gdal.ReprojectImage(src,dst,src_epsg.ExportToWkt(),dst_epsg.ExportToWkt(),resample_technique)

        else:
            dst = gdal.Warp('',src,dstSRS="EPSG:"+str(to_epsg),format='VRT')

        return dst


    @staticmethod
    def ReprojectDataset(src, to_epsg=3857, cell_size=[], resample_technique="Nearest"):
        """
        =====================================================================
         reproject_dataset(src, to_epsg=3857, pixel_spacing=[]):
        =====================================================================
        this function reproject and resample a raster to any projection
        (default the WGS84 web mercator projection, without resampling)
        The function returns a GDAL in-memory file object, where you can ReadAsArray etc.

        inputs:
        ----------
            1- raster:
                gdal dataset (src=gdal.Open("dem.tif"))
            2-to_epsg:
                integer reference number to the new projection (https://epsg.io/)
                (default 3857 the reference no of WGS84 web mercator )
            3-cell_size:
                integer number to resample the raster cell size to a new cell size
                (default empty so raster will not be resampled)
            4- resample_technique:
                [String] resampling technique default is "Nearest"
                https://gisgeography.com/raster-resampling/
                "Nearest" for nearest neighbour,"cubic" for cubic convolution,
                "bilinear" for bilinear

        Outputs:
        ----------
            1-raster:
                gdal dataset (you can read it by ReadAsArray)
        """
        # input data validation
        # type of inputs
        assert type(src)==gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(to_epsg)==int,"please enter correct integer number for to_epsg more information https://epsg.io/"
        assert type(resample_technique)== str ," please enter correct resample_technique more information see docmentation "
        if cell_size != []:
            assert type(cell_size)== int or type(cell_size)== float , "please enter an integer or float cell size"

        if resample_technique=="Nearest":
            resample_technique=gdal.GRA_NearestNeighbour
        elif resample_technique=="cubic":
            resample_technique=gdal.GRA_Cubic
        elif resample_technique=="bilinear":
            resample_technique=gdal.GRA_Bilinear

    #    # READ THE RASTER
    #    src = gdal.Open(inputspath+"dem_4km.tif")
        # GET PROJECTION
        src_proj=src.GetProjection()
        # GET THE GEOTRANSFORM
        src_gt=src.GetGeoTransform()
        # GET NUMBER OF columns
        src_x=src.RasterXSize
        # get number of rows
        src_y=src.RasterYSize
        # number of bands
    #    src_bands=src.RasterCount
        # spatial ref
        src_epsg=osr.SpatialReference(wkt=src_proj)

        # distination
        # spatial ref
        dst_epsg=osr.SpatialReference()
        dst_epsg.ImportFromEPSG(to_epsg)
        # transformation factors
        tx = osr.CoordinateTransformation(src_epsg,dst_epsg)

        # incase the source crs is GCS and longitude is in the west hemisphere gdal
        # reads longitude fron 0 to 360 and transformation factor wont work with valeus
        # greater than 180
        if src_epsg.GetAttrValue('AUTHORITY',1)=="4326" and src_gt[0] > 180:
            lng_new=src_gt[0]-360
            # transform the right upper corner point
            (ulx,uly,ulz) = tx.TransformPoint(lng_new, src_gt[3])
            # transform the right lower corner point
            (lrx,lry,lrz)=tx.TransformPoint(lng_new+src_gt[1]*src_x,
                                            src_gt[3]+src_gt[5]*src_y)
        else:
            # transform the right upper corner point
            (ulx,uly,ulz) = tx.TransformPoint(src_gt[0], src_gt[3])
            # transform the right lower corner point
            (lrx,lry,lrz)=tx.TransformPoint(src_gt[0]+src_gt[1]*src_x,
                                            src_gt[3]+src_gt[5]*src_y)

        if cell_size==[]:
        # the result raster has the same pixcel size as the source
            # check if the coordinate system is GCS convert the distance from angular to metric
            if src_epsg.GetAttrValue('AUTHORITY',1)=="4326":
                coords_1 = (src_gt[3], src_gt[0])
                coords_2 = (src_gt[3], src_gt[0]+src_gt[1])
    #            pixel_spacing=geopy.distance.vincenty(coords_1, coords_2).m
                pixel_spacing = Vector.GCSDistance(coords_1, coords_2)
            else:
                pixel_spacing=src_gt[1]
        else:
            assert (cell_size > 1),"please enter cell size greater than 1"
        # if the user input a cell size resample the raster
            pixel_spacing=cell_size

        # create a new raster
        mem_drv=gdal.GetDriverByName("MEM")
        dst=mem_drv.Create("",int(np.round(abs(lrx-ulx)/pixel_spacing)),int(np.round(abs(uly-lry)/pixel_spacing)),
                           1,gdalconst.GDT_Float32) # ['COMPRESS=LZW'] LZW is a lossless compression method achieve the highst compression but with lot of computation

        # new geotransform
        new_geo=(ulx,pixel_spacing,src_gt[2],uly,src_gt[4],-pixel_spacing)
        # set the geotransform
        dst.SetGeoTransform(new_geo)
        # set the projection
        dst.SetProjection(dst_epsg.ExportToWkt())
        # set the no data value
        dst.GetRasterBand(1).SetNoDataValue(src.GetRasterBand(1).GetNoDataValue())
        # initialize the band with the nodata value instead of 0
        dst.GetRasterBand(1).Fill(src.GetRasterBand(1).GetNoDataValue())
        # perform the projection & resampling
        gdal.ReprojectImage(src,dst,src_epsg.ExportToWkt(),dst_epsg.ExportToWkt(),resample_technique)

        return dst

    @staticmethod
    def RasterLike(src,array,path,pixel_type=1):
        """
        ====================================================================
          RasterLike(src,array,path)
        ====================================================================
        RasterLike method creates a Geotiff raster like another input raster, new raster
        will have the same projection, coordinates or the top left corner of the original
        raster, cell size, nodata velue, and number of rows and columns
        the raster and the dem should have the same number of columns and rows

        inputs:
        ----------
            1- src:
                [gdal.dataset] source raster to get the spatial information
            2- array:
                [numpy array]to store in the new raster
            3- path:
                [String] path to save the new raster including new raster name and extension (.tif)
            4-pixel_type:
                [integer] type of the data to be stored in the pixels,default is 1 (float32)
                for example pixel type of flow direction raster is unsigned integer
                1 for float32
                2 for float64
                3 for Unsigned integer 16
                4 for Unsigned integer 32
                5 for integer 16
                6 for integer 32

        outputs:
        ----------
            1- save the new raster to the given path

        Ex:
        ----------
            data=np.load("RAIN_5k.npy")
            src=gdal.Open("DEM.tif")
            name="rain.tif"
            RasterLike(src,data,name)
        """
        # input data validation
        # data type
        assert type(src) == gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(array) == np.ndarray, "array should be of type numpy array"
        assert type(path) == str, "Raster_path input should be string type"
        assert type(pixel_type) == int, "pixel type input should be integer type please check documentations"
        # input values
    #    assert os.path.exists(path), path+ " you have provided does not exist"
        ext = path[-4:]
        assert ext == ".tif", "please add the extension at the end of the path input"
    #    assert os.path.exists(path), "source raster you have provided does not exist"

        prj = src.GetProjection()
        cols = src.RasterXSize
        rows = src.RasterYSize
        gt = src.GetGeoTransform()
        noval = src.GetRasterBand(1).GetNoDataValue()
        if pixel_type == 1:
            dst = gdal.GetDriverByName('GTiff').Create(path,cols,rows,1,gdal.GDT_Float32)
        elif pixel_type == 2:
            dst = gdal.GetDriverByName('GTiff').Create(path,cols,rows,1,gdal.GDT_Float64)
        elif pixel_type == 3:
            dst = gdal.GetDriverByName('GTiff').Create(path,cols,rows,1,gdal.GDT_UInt16)
        elif pixel_type == 4:
            dst = gdal.GetDriverByName('GTiff').Create(path,cols,rows,1,gdal.GDT_UInt32)
        elif pixel_type == 5:
            dst = gdal.GetDriverByName('GTiff').Create(path,cols,rows,1,gdal.GDT_Int16)
        elif pixel_type == 6:
            dst = gdal.GetDriverByName('GTiff').Create(path,cols,rows,1,gdal.GDT_Int32)

        dst.SetGeoTransform(gt)
        dst.SetProjection(prj)
        # setting the NoDataValue does not accept double precision numbers
        try:
            dst.GetRasterBand(1).SetNoDataValue(noval)
            dst.GetRasterBand(1).Fill(noval)
        except:
            noval = -999999
            dst.GetRasterBand(1).SetNoDataValue(noval)
            dst.GetRasterBand(1).Fill(noval)
            # assert False, "please change the NoDataValue in the source raster as it is not accepted by Gdal"
            print("please change the NoDataValue in the source raster as it is not accepted by Gdal")

        dst.GetRasterBand(1).WriteArray(array)
        dst.FlushCache()
        dst = None

    @staticmethod
    def MatchNoDataValue(src, dst):
        """
        ==================================================================
          MatchNoDataValue(src,dst)
        ==================================================================
        this function matches the location of nodata value from src raster to dst
        raster, Both rasters have to have the same dimensions (no of rows & columns)
        so MatchRasterAlignment should be used prior to this function to align both
        rasters


        inputs:
        ----------
            1-src:
                [gdal.dataset] source raster to get the location of the NoDataValue and
                where it is in the array
            1-dst:
                [gdal.dataset] raster you want to store NoDataValue in its cells
                exactly the same like src raster

        Outputs:
        ----------
            1- dst:
                [gdal.dataset] the second raster with NoDataValue stored in its cells
                exactly the same like src raster
        """
        # input data validation
        # data type
        assert type(src)==gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(dst)==gdal.Dataset, "dst should be read using gdal (gdal dataset please read it using gdal library) "

        src_gt = src.GetGeoTransform()
        src_proj = src.GetProjection()
        src_row = src.RasterYSize
        src_col = src.RasterXSize
        src_noval = src.GetRasterBand(1).GetNoDataValue()
        src_sref = osr.SpatialReference(wkt=src_proj)
        src_epsg = int(src_sref.GetAttrValue('AUTHORITY',1))

        src_array = src.ReadAsArray()

        dst_gt = dst.GetGeoTransform()
        dst_proj = dst.GetProjection()
        dst_row = dst.RasterYSize
        dst_col = dst.RasterXSize

        dst_sref = osr.SpatialReference(wkt=dst_proj)
        dst_epsg = int(dst_sref.GetAttrValue('AUTHORITY',1))

        #check proj
        assert src_row == dst_row and src_col==dst_col, "two rasters has different no of columns or rows please resample or match both rasters"
        assert dst_gt == src_gt, "location of upper left corner of both rasters are not the same or cell size is different please match both rasters first "
        assert src_epsg == dst_epsg, "Raster A & B are using different coordinate system please reproject one of them to the other raster coordinate system"

        dst_array = dst.ReadAsArray()
        if src_array.dtype == np.float32:
            dst_array[src_array == np.float32(src_noval)] = np.float32(src_noval)
        else:
            dst_array[src_array == np.float64(src_noval)] = np.float64(src_noval)

        # align function only equate the no of rows and columns only
        # match nodatavalue inserts nodatavalue in dst raster to all places like src
        # still places that has nodatavalue in the dst raster but it is not nodatavalue in the src
        # and now has to be filled with values
        # compare no of element that is not nodata value in both rasters to make sure they are matched
        elem_src = np.size(src_array[:,:])-np.count_nonzero((src_array[src_array==src_noval]))
        elem_dst = np.size(dst_array[:,:])-np.count_nonzero((dst_array[dst_array==src_noval]))
        # if not equal then store indices of those cells that doesn't matchs
        if elem_src > elem_dst :
            rows=[i for i in range(src_row) for j in range(src_col) if dst_array[i,j]==src_noval and src_array[i,j] != src_noval]
            cols=[j for i in range(src_row) for j in range(src_col) if dst_array[i,j]==src_noval and src_array[i,j] != src_noval]
        # interpolate those missing cells by nearest neighbour
        if elem_src > elem_dst :
            dst_array = Raster.NearestNeighbour(dst_array, src_noval, rows, cols)


        mem_drv=gdal.GetDriverByName("MEM")
        dst=mem_drv.Create("",src_col,src_row,1,gdalconst.GDT_Float32) #,['COMPRESS=LZW'] LZW is a lossless compression method achieve the highst compression but with lot of computation

        # set the geotransform
        dst.SetGeoTransform(src_gt)
        # set the projection
        dst.SetProjection(src_sref.ExportToWkt())
        # set the no data value
        dst.GetRasterBand(1).SetNoDataValue(src.GetRasterBand(1).GetNoDataValue())
        # initialize the band with the nodata value instead of 0
        dst.GetRasterBand(1).Fill(src.GetRasterBand(1).GetNoDataValue())
        dst.GetRasterBand(1).WriteArray(dst_array)

        return dst

    @staticmethod
    def ChangeNoDataValue(src,dst):
        """
        ==================================================================
          ChangeNoDataValue(src,dst)
        ==================================================================
        this function changes the value of nodata value in a dst raster to be like
        a src raster.

        inputs:
        ----------
            1-src:
                [gdal.dataset] source raster to get the location of the NoDataValue and
                where it is in the array
            1-dst:
                [gdal.dataset] raster you want to store NoDataValue in its cells
                exactly the same like src raster

        Outputs:
        ----------
            1- dst:
                [gdal.dataset] the second raster with NoDataValue stored in its cells
                exactly the same like src raster
        """
        # input data validation
        # data type
        assert type(src)==gdal.Dataset, "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(dst)==gdal.Dataset, "dst should be read using gdal (gdal dataset please read it using gdal library) "

        src_noval=np.float32(src.GetRasterBand(1).GetNoDataValue())

        dst_gt = dst.GetGeoTransform()
        dst_proj = dst.GetProjection()
        dst_row = dst.RasterYSize
        dst_col = dst.RasterXSize
        dst_noval = np.float32(dst.GetRasterBand(1).GetNoDataValue())
        dst_sref = osr.SpatialReference(wkt=dst_proj)
    #    dst_epsg = int(dst_sref.GetAttrValue('AUTHORITY',1))

        dst_array = dst.ReadAsArray()
        dst_array[dst_array==dst_noval]=src_noval

        mem_drv=gdal.GetDriverByName("MEM")
        dst=mem_drv.Create("",dst_col,dst_row,1,gdalconst.GDT_Float32) #,['COMPRESS=LZW'] LZW is a lossless compression method achieve the highst compression but with lot of computation

        # set the geotransform
        dst.SetGeoTransform(dst_gt)
        # set the projection
        dst.SetProjection(dst_sref.ExportToWkt())
        # set the no data value
        dst.GetRasterBand(1).SetNoDataValue(src.GetRasterBand(1).GetNoDataValue())
        # initialize the band with the nodata value instead of 0
        dst.GetRasterBand(1).Fill(src.GetRasterBand(1).GetNoDataValue())
        dst.GetRasterBand(1).WriteArray(dst_array)

        return dst

    @staticmethod
    def MatchRasterAlignment(RasterA,RasterB):
        """
        =========================================================================
          MatchRasterAlignment(RasterA,RasterB)
        =========================================================================
        this function matches the coordinate system and the number of of rows & columns
        between two rasters
        Raster A is the source of the coordinate system, no of rows and no of columns & cell size
        Raster B is the source of data values in cells
        the result will be a raster with the same structure like RasterA but with
        values from RasterB using Nearest Neighbour interpolation algorithm

        Inputs:
        ----------
            1- RasterA:
                [gdal.dataset] spatial information source raster to get the spatial information
                (coordinate system, no of rows & columns)
            2- RasterB:
                [gdal.dataset] data values source raster to get the data (values of each cell)

        Outputs:
        ----------
            1- dst:
                [gdal.dataset] result raster in memory

        Example:
        ----------
            A=gdal.Open("dem4km.tif")
            B=gdal.Open("P_CHIRPS.v2.0_mm-day-1_daily_2009.01.06.tif")
            matched_raster=MatchRasters(A,B)
        """
        # input data validation
        # data type
        assert type(RasterA) == gdal.Dataset, "RasterA should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(RasterB) == gdal.Dataset, "RasterB should be read using gdal (gdal dataset please read it using gdal library) "

        gt_src = RasterA
        # we need number of rows and cols from src A and data from src B to store both in dst
        gt_src_proj = gt_src.GetProjection()
        # GET THE GEOTRANSFORM
        gt_src_gt = gt_src.GetGeoTransform()
        # GET NUMBER OF columns
        gt_src_x = gt_src.RasterXSize
        # get number of rows
        gt_src_y = gt_src.RasterYSize

        gt_src_epsg = osr.SpatialReference(wkt=gt_src_proj)
    #    gt_src_epsg.GetAttrValue('AUTHORITY',1)

        # unite the crs
        data_src = Raster.ProjectRaster(RasterB,int(gt_src_epsg.GetAttrValue('AUTHORITY',1)))

        # create a new raster
        mem_drv=gdal.GetDriverByName("MEM")
        dst = mem_drv.Create("",gt_src_x,gt_src_y,1,gdalconst.GDT_Float32) #,['COMPRESS=LZW'] LZW is a lossless compression method achieve the highst compression but with lot of computation
        # set the geotransform
        dst.SetGeoTransform(gt_src_gt)
        # set the projection
        dst.SetProjection(gt_src_epsg.ExportToWkt())
        # set the no data value
        dst.GetRasterBand(1).SetNoDataValue(gt_src.GetRasterBand(1).GetNoDataValue())
        # initialize the band with the nodata value instead of 0
        dst.GetRasterBand(1).Fill(gt_src.GetRasterBand(1).GetNoDataValue())
        # perform the projection & resampling
        resample_technique = gdal.GRA_NearestNeighbour #gdal.GRA_NearestNeighbour

        gdal.ReprojectImage(data_src,dst,gt_src_epsg.ExportToWkt(),gt_src_epsg.ExportToWkt(),resample_technique)

        return dst

    @staticmethod
    def NearestNeighbour(array, Noval, rows, cols):
        """
        ===============================================================
            NearestNeighbour(array, Noval, rows, cols)
        ===============================================================
        this function filles cells of a given indices in rows and cols with
        the value of the nearest neighbour.
        as the raster grid is square so the 4 perpendicular direction are of the same
        close so the function give priority to the right then left then bottom then top
        and the same for 45 degree inclined direction right bottom then left bottom
        then left Top then right Top

        Inputs:
        ----------
            1-array:
                [numpy.array] Array to fill some of its cells with Nearest value.
            2-Noval:
                [float32] value stored in cells that is out of the domain
            3-rows:
                [List] list of the row index of the cells you want to fill it with
                nearest neighbour.
            4-cols:
                [List] list of the column index of the cells you want to fill it with
                nearest neighbour.

        Output:
        ----------
            - array:
                [numpy array] Cells of given indices will be filled with value of the Nearest neighbour

        Example:
        ----------
            - raster=gdal.opne("dem.tif")
              rows=[3,12]
              cols=[9,2]
              new_array=NearestNeighbour(rasters, rows, cols)
        """
        # input data validation
        # data type
        assert type(array)==np.ndarray , "src should be read using gdal (gdal dataset please read it using gdal library) "
        assert type(rows) == list,"rows input has to be of type list"
        assert type(cols) == list,"cols input has to be of type list"


    #    array=raster.ReadAsArray()
    #    Noval=np.float32(raster.GetRasterBand(1).GetNoDataValue())
    #    no_rows=raster.RasterYSize
        no_rows=np.shape(array)[0]
    #    no_cols=raster.RasterXSize
        no_cols=np.shape(array)[1]

        for i in range(len(rows)):
            # give the cell the value of the cell that is at the right
            if array[rows[i],cols[i]+1] != Noval and cols[i]+1 <= no_cols:
                array[rows[i],cols[i]] = array[rows[i],cols[i]+1]

            elif array[rows[i],cols[i]-1] != Noval and cols[i]-1 > 0 :
                # give the cell the value of the cell that is at the left
                array[rows[i],cols[i]] = array[rows[i],cols[i]-1]

            elif array[rows[i]-1,cols[i]] != Noval and rows[i]-1 > 0:
            # give the cell the value of the cell that is at the bottom
                array[rows[i],cols[i]] = array[rows[i]-1,cols[i]]

            elif array[rows[i]+1,cols[i]] != Noval and rows[i]+1 <= no_rows:
            # give the cell the value of the cell that is at the Top
                array[rows[i],cols[i]] = array[rows[i]+1,cols[i]]

            elif array[rows[i]-1,cols[i]+1] != Noval and rows[i]-1 > 0 and cols[i]+1 <=no_cols :
            # give the cell the value of the cell that is at the right bottom
                array[rows[i],cols[i]] = array[rows[i]-1,cols[i]+1]

            elif array[rows[i]-1,cols[i]-1] != Noval and rows[i]-1 >0 and cols[i]-1 > 0:
            # give the cell the value of the cell that is at the left bottom
                array[rows[i],cols[i]] = array[rows[i]-1,cols[i]-1]

            elif array[rows[i]+1,cols[i]-1] != Noval and rows[i]+1 <= no_rows and cols[i]-1 > 0:
            # give the cell the value of the cell that is at the left Top
                array[rows[i],cols[i]] = array[rows[i]+1,cols[i]-1]

            elif array[rows[i]+1,cols[i]+1] != Noval and rows[i]+1 <= no_rows and cols[i]+1 <= no_cols:
            # give the cell the value of the cell that is at the right Top
                array[rows[i],cols[i]] = array[rows[i]+1,cols[i]+1]
            else:
                print("the cell is isolated (No surrounding cells exist)")
        return array

    @staticmethod
    def ReadASCII(ASCIIFile,pixel_type=1):
        """
        =========================================================================
            ReadASCII(ASCIIFile,pixel_type)
        =========================================================================

        This function reads an ASCII file the spatial information

        Inputs:
            1-ASCIIFileName:
                [String] name of the ASCII file you want to convert and the name
                should include the extension ".asc"

            2-pixel_type:
                [Integer] type of the data to be stored in the pixels,default is 1 (float32)
                for example pixel type of flow direction raster is unsigned integer
                1 for float32
                2 for float64
                3 for Unsigned integer 16
                4 for Unsigned integer 32
                5 for integer 16
                6 for integer 32
        Outputs:
            1-ASCIIValues:
                [numpy array] 2D arrays containing the values stored in the ASCII
                file

            2-ASCIIDetails:
                [List] list of the six spatial information of the ASCII file
                [ASCIIRows, ASCIIColumns, XLowLeftCorner, YLowLeftCorner,
                CellSize, NoValue]
        Example:
            Elevation_values,DEMSpatialDetails = ReadASCII("dem.asc",1)
        """
        # input data validation
        # data type
        assert type(ASCIIFile) == str, "ASCIIFile input should be string type"
        assert type(pixel_type)== int, "pixel type input should be integer type please check documentations"

        # input values
        ASCIIExt=ASCIIFile[-4:]
        assert ASCIIExt == ".asc", "please add the extension at the end of the path input"
        assert os.path.exists(ASCIIFile), "ASCII file path you have provided does not exist"

        ### read the ASCII file

        File  = open (ASCIIFile)
        Wholefile = File.readlines()
        File.close()

        ASCIIColumns = int(Wholefile[0].split()[1])
        ASCIIRows = int(Wholefile[1].split()[1])

        XLeftSide = int(float(Wholefile[2].split()[1]))
        YLowerSide = int(float(Wholefile[3].split()[1]))
        CellSize = int(Wholefile[4].split()[1])
        NoValue = int(Wholefile[5].split()[1])

        ASCIIValues = np.ones((ASCIIRows,ASCIIColumns), dtype = np.float32)
        try:
            for i in range(ASCIIRows):
                x = Wholefile[6+i].split()
                ASCIIValues[i,:] = list(map(float, x ))
        except:
            try:
                for j in range(len(x)):
                    float(x[j])
            except:
                print("Error reading the ARCII file please check row " + str(i+6+1) +", column " + str(j))
                print("A value of " + x[j] + " , is stored in the ASCII file ")

        ASCIIDetails = [ASCIIRows, ASCIIColumns, XLeftSide , YLowerSide,
                        CellSize, NoValue]

        return ASCIIValues, ASCIIDetails

    @staticmethod
    def StringSpace(Inp):
        return str(Inp) + "  "

    @staticmethod
    def WriteASCII(ASCIIFile, ASCIIDetails, ASCIIValues):
        """
        =========================================================================
            WriteASCII(ASCIIFile, ASCIIDetails, ASCIIValues, pixel_type=1)
        =========================================================================

        This function reads an ASCII file the spatial information

        Inputs:
            1-ASCIIFile:
                [String] name of the ASCII file you want to convert and the name
                should include the extension ".asc"

            2-ASCIIDetails:
                [List] list of the six spatial information of the ASCII file
                [ASCIIRows, ASCIIColumns, XLowLeftCorner, YLowLeftCorner,
                CellSize, NoValue]

            3-ASCIIValues:
                [numpy array] 2D arrays containing the values stored in the ASCII
                file

        Outputs:

        Example:
            Elevation_values,DEMSpatialDetails = ReadASCII("dem.asc",1)
        """
        # input data validation
        # data type
        assert type(ASCIIFile) == str, "ASCIIFile input should be string type"

        # input values
        ASCIIExt=ASCIIFile[-4:]
        assert ASCIIExt == ".asc", "please add the extension at the end of the path input"
    #    assert os.path.exists(ASCIIFile), "ASCII file path you have provided does not exist"

        ### read the ASCII file
        try:
            File  = open (ASCIIFile,'w')
        except:
            print("path you have provided does not exist")
            print("please check" + ASCIIFile)

        # write the the ASCII file details
        File.write('ncols         ' + str(ASCIIDetails[1])+ "\n")
        File.write('nrows         ' + str(ASCIIDetails[0])+ "\n")
        File.write('xllcorner     ' + str(ASCIIDetails[2])+ "\n")
        File.write('yllcorner     ' + str(ASCIIDetails[3])+ "\n")
        File.write('cellsize      ' + str(ASCIIDetails[4])+ "\n")
        File.write('NODATA_value  ' + str(ASCIIDetails[5])+ "\n")

        # write the array
        for i in range(np.shape(ASCIIValues)[0]):
            File.writelines(list(map(Raster.StringSpace,ASCIIValues[i,:])))
            File.write("\n")

        File.close()

    @staticmethod
    def ASCIItoRaster(ASCIIFile,savePath,pixel_type=1,RasterFile = None,epsg = None):
        """
        =========================================================================
            ASCIItoRaster(ASCIIFile,savePath,pixel_type=1,RasterFile = None,epsg = None)
        =========================================================================

        This function convert an ASCII file into a raster format and in takes  all
        the spatial information (projection, coordinates of the corner point), and
        number of rows and columns from raster file or you have to define the epsg corresponding
        to the you coordinate system and projection

        Inputs:
            1-ASCIIFileName:
                [String] name of the ASCII file you want to convert and the name
                should include the extension ".asc"

            2-savePath:
                [String] path to save the new raster including new raster name and extension (.tif)

            3-pixel_type:
                [Integer] type of the data to be stored in the pixels,default is 1 (float32)
                for example pixel type of flow direction raster is unsigned integer
                1 for float32
                2 for float64
                3 for Unsigned integer 16
                4 for Unsigned integer 32
                5 for integer 16
                6 for integer 32

            4-RasterFile:
                [String] source raster to get the spatial information, both ASCII
                file and source raster should have the same number of rows, and
                same number of columns default value is [None].

            5-epsg:
                EPSG stands for European Petroleum Survey Group and is an organization
                that maintains a geodetic parameter database with standard codes,
                the EPSG codes, for coordinate systems, datums, spheroids, units
                and such alike (https://epsg.io/) default value is [None].

        Outputs:
            1- a New Raster will be saved in the savePath containing the values
            of the ASCII file

        Example:
            1- ASCII to raster given a raster file:
                ASCIIFile = "soiltype.asc"
                RasterFile = "DEM.tif"
                savePath = "Soil_raster.tif"
                pixel_type = 1
                ASCIItoRaster(ASCIIFile,  savePath, pixel_type, RasterFile)
            2- ASCII to Raster given an EPSG number
                ASCIIFile = "soiltype.asc"
                savePath = "Soil_raster.tif"
                pixel_type = 1
                epsg = 4647
            ASCIItoRaster(ASCIIFile, savePath,pixel_type, epsg = epsg)
        """
        # input data validation
        # data type
        assert type(ASCIIFile) == str, "ASCIIFile input should be string type"
        assert type(savePath) == str, "savePath input should be string type"
        assert type(pixel_type)== int, "pixel type input should be integer type please check documentations"

        # input values
        ASCIIExt=ASCIIFile[-4:]
        assert ASCIIExt == ".asc", "please add the extension at the end of the path input"

        # assert os.path.exists(path), "source raster you have provided does not exist"

        # check what does the user enter
    #    try: RasterFile
    #    except NameError : RasterFile = None

    #    try: epsg
    #    except NameError : epsg = None

        message = """ you have to enter one of the following inputs
        - RasterFile : if you have a raster with the same spatial information
            (projection, coordinate system), and have the same number of rows,
            and columns
        - epsg : if you have the EPSG number (https://epsg.io/) refering to
            the spatial information of the ASCII file
        """
        assert RasterFile != None or epsg != None, message

        ### read the ASCII file
        ASCIIValues, ASCIIDetails = Raster.ReadASCII(ASCIIFile,pixel_type)
        ASCIIRows = ASCIIDetails[0]
        ASCIIColumns = ASCIIDetails[1]

        # check the optional inputs
        if RasterFile != None :
            assert type(RasterFile) == str, "RasterFile input should be string type"

            RasterExt=RasterFile[-4:]
            assert RasterExt == ".tif", "please add the extension at the end of the path input"
            # read the raster file
            src = gdal.Open(RasterFile)
            RasterColumns = src.RasterXSize
            RasterRows = src.RasterYSize

            assert ASCIIRows == RasterRows and ASCIIColumns == RasterColumns, " Data in both ASCII file and Raster file should have the same number of row and columns"

            Raster.RasterLike(src,ASCIIValues, savePath, pixel_type)
        elif epsg != None :
            assert type(epsg)== int, "epsg input should be integer type please check documentations"
            # coordinates of the lower left corner
            XLeftSide  = ASCIIDetails[2]
    #        YLowSide = ASCIIDetails[3]

            CellSize = ASCIIDetails[4]
            NoValue = ASCIIDetails[5]
            # calculate Geotransform coordinates for the raster
            YUpperSide = ASCIIDetails[3] + ASCIIRows * CellSize

            dst_gt = (XLeftSide, CellSize, 0.0, YUpperSide, 0.0, -1*CellSize)
            dst_epsg=osr.SpatialReference()
            dst_epsg.ImportFromEPSG(epsg)

            if pixel_type==1:
                dst=gdal.GetDriverByName('GTiff').Create(savePath,ASCIIColumns,ASCIIRows,1,gdal.GDT_Float32)
            elif pixel_type==2:
                dst=gdal.GetDriverByName('GTiff').Create(savePath,ASCIIColumns,ASCIIRows,1,gdal.GDT_Float64)
            elif pixel_type==3:
                dst=gdal.GetDriverByName('GTiff').Create(savePath,ASCIIColumns,ASCIIRows,1,gdal.GDT_UInt16)
            elif pixel_type==4:
                dst=gdal.GetDriverByName('GTiff').Create(savePath,ASCIIColumns,ASCIIRows,1,gdal.GDT_UInt32)
            elif pixel_type==5:
                dst=gdal.GetDriverByName('GTiff').Create(savePath,ASCIIColumns,ASCIIRows,1,gdal.GDT_Int16)
            elif pixel_type==6:
                dst=gdal.GetDriverByName('GTiff').Create(savePath,ASCIIColumns,ASCIIRows,1,gdal.GDT_Int32)

            dst.SetGeoTransform(dst_gt)
            dst.SetProjection(dst_epsg.ExportToWkt())
            dst.GetRasterBand(1).SetNoDataValue(NoValue)
            dst.GetRasterBand(1).Fill(NoValue)
            dst.GetRasterBand(1).WriteArray(ASCIIValues)
            dst.FlushCache()
            dst = None




    @staticmethod
    def ClipRasterWithPolygon(Raster_path,shapefile_path,save=False,output_path=None):
        """
        =========================================================================
          ClipRasterWithPolygon(Raster_path, shapefile_path, output_path)
        =========================================================================
        this function clip a raster using polygon shapefile

        inputs:
        ----------
            1- Raster_path:
                [String] path to the input raster including the raster extension (.tif)
            2- shapefile_path:
                [String] path to the input shapefile including the shapefile extension (.shp)
            3-save:
                [Boolen] True or False to decide whether to save the clipped raster or not
                default is False
            3- output_path:
                [String] path to the place in your drive you want to save the clipped raster
                including the raster name & extension (.tif), default is None

        Outputs:
        ----------
            1- projected_raster:
                [gdal object] clipped raster
            2- if save is True function is going to save the clipped raster to the output_path

        EX:
        ----------
            import plotting_function as plf
            Raster_path = r"data/Evaporation_ERA-Interim_2009.01.01.tif"
            shapefile_path ="data/"+"Outline.shp"
            clipped_raster=plf.ClipRasterWithPolygon(Raster_path,shapefile_path)
            or
            output_path = r"data/cropped.tif"
            clipped_raster=ClipRasterWithPolygon(Raster_path,shapefile_path,True,output_path)
        """
        # input data validation
        # type of inputs
        assert type(Raster_path)== str, "Raster_path input should be string type"
        assert type(shapefile_path)== str, "shapefile_path input should be string type"
        assert type(save)== bool , "save input should be bool type (True or False)"
        if save == True:
            assert type(output_path)== str," pleaase enter a path to save the clipped raster"
        # inputs value
        if save == True:
            ext=output_path[-4:]
            assert ext == ".tif", "please add the extention at the end of the output_path input"

        raster = gdal.Open(Raster_path)
        proj = raster.GetProjection()
        src_epsg = osr.SpatialReference(wkt=proj)
        gt = raster.GetGeoTransform()

        # first check if the crs is GCS if yes check whether the long is greater than 180
        # geopandas read -ve longitude values if location is west of the prime meridian
        # while rasterio and gdal not
        if src_epsg.GetAttrValue('AUTHORITY',1) == "4326" and gt[0] > 180:
            # reproject the raster to web mercator crs
            raster = Raster.ReprojectDataset(raster)
            out_transformed = os.environ['Temp']+"/transformed.tif"
            # save the raster with the new crs
            Raster.SaveRaster(raster,out_transformed)
            raster = rasterio.open(out_transformed)
        else:
            # crs of the raster was not GCS or longitudes are less than 180
            raster = rasterio.open(Raster_path)

        ### Cropping the raster with the shapefile
        # read the shapefile
        shpfile = gpd.read_file(shapefile_path)
        # Re-project into the same coordinate system as the raster data
        shpfile = shpfile.to_crs(crs=raster.crs.data)

        def getFeatures(gdf):
            """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""

            return [json.loads(gdf.to_json())['features'][0]['geometry']]

        # Get the geometry coordinates by using the function.
        coords = getFeatures(shpfile)

        out_img, out_transform = rasterio.mask.mask(dataset=raster, shapes=coords, crop=True)

        # copy the metadata from the original data file.
        out_meta = raster.meta.copy()

        # Next we need to parse the EPSG value from the CRS so that we can create
        #a Proj4 string using PyCRS library (to ensure that the projection information is saved correctly).
        epsg_code = int(raster.crs.data['init'][5:])

        # Now we need to update the metadata with new dimensions, transform (affine) and CRS (as Proj4 text)
        out_meta.update({"driver": "GTiff",
                            "height": out_img.shape[1],
                            "width": out_img.shape[2],
                            "transform": out_transform,
                            "crs": pyproj.CRS.from_epsg(epsg_code).to_wkt()
                        }
                      )

        # save the clipped raster.
        temp_path = os.environ['Temp'] + "/cropped.tif"
        with rasterio.open(temp_path,"w", **out_meta) as dest:
            dest.write(out_img)

        # close the transformed raster
        raster.close()
        # delete the transformed raster
        os.remove(out_transformed)
        # read the clipped raster
        raster = gdal.Open(temp_path)
        # reproject the clipped raster back to its original crs
        projected_raster = Raster.ProjectRaster(raster,int(src_epsg.GetAttrValue('AUTHORITY',1)))
        # close the clipped raster
        raster = None

        # delete the clipped raster
        os.remove(temp_path)
        # write the raster to the file
        if save:
            Raster.SaveRaster(projected_raster,output_path)

        return projected_raster

    @staticmethod
    def Clip2(Rasterobj, Polygongdf, Save=False, out_tif='masked.tif'):
        """
        =====================================================================
            Clip(Rasterobj, Polygongdf, Save=False, out_tif='masked.tif')
        =====================================================================
        Clip function takes a rasterio object and clip it with a given geodataframe
        containing a polygon shapely object

        Parameters
        ----------
        Rasterobj : [rasterio.io.DatasetReader]
            the raster read by rasterio .
        Polygongdf : [geodataframe]
            geodataframe containing the polygon you want clip the raster based on.
        Save : [Bool], optional
            to save the clipped raster to your drive. The default is False.
        out_tif : [String], optional
            path iincluding the extention (.tif). The default is 'masked.tif'.

        Returns
        -------
        1-out_img : [rasterio object]
            the clipped raster.

        2-metadata : [dictionay]
                dictionary containing number of bands, coordinate reference system crs
                dtype, geotransform, height and width of the raster

        """
        ### 1- Re-project the polygon into the same coordinate system as the raster data.
        # We can access the crs of the raster using attribute .crs.data:

        # Project the Polygon into same CRS as the grid
        Polygongdf = Polygongdf.to_crs(crs=Rasterobj.crs.data)

        # Print crs
        # geo.crs
        ### 2- Convert the polygon into GeoJSON format for rasterio.

        # Get the geometry coordinates by using the function.
        coords = [json.loads(Polygongdf.to_json())['features'][0]['geometry']]

        # print(coords)

        ### 3-Clip the raster with Polygon
        out_img, out_transform = rasterio.mask.mask(dataset=Rasterobj, shapes=coords, crop=True)

        ### 4- update the metadata
        # Copy the old metadata
        out_meta = Rasterobj.meta.copy()
        # print(out_meta)

        # Next we need to parse the EPSG value from the CRS so that we can create
        # a Proj4 -string using PyCRS library (to ensure that the projection
        # information is saved correctly).

        # Parse EPSG code
        epsg_code = int(Rasterobj.crs.data['init'][5:])
        # print(epsg_code)


        out_meta.update({"driver": "GTiff",
                         "height": out_img.shape[1],
                         "width": out_img.shape[2],
                         "transform": out_transform,
                         "crs": pyproj.CRS.from_epsg(epsg_code).to_wkt()}
                                 )
        if Save :
            with rasterio.open(out_tif, "w", **out_meta) as dest:
                    dest.write(out_img)

        return out_img, out_meta

    @staticmethod
    def ClipRasterWithRaster(RasterTobeClippedPath,SourceRasterPath, OutputPath='', Save=False):

        # get information from the source raster
        gt_src = gdal.Open(SourceRasterPath) #, GA_ReadOnly
        # we need number of rows and cols from src A and data from src B to store both in dst
        gt_src_proj = gt_src.GetProjection()
        # GET THE GEOTRANSFORM
        gt_src_gt = gt_src.GetGeoTransform()
        # GET NUMBER OF columns
        gt_src_x = gt_src.RasterXSize
        # get number of rows
        gt_src_y = gt_src.RasterYSize

        gt_src_epsg = osr.SpatialReference(wkt=gt_src_proj)

        mem_drv = gdal.GetDriverByName("MEM")
        dst = mem_drv.Create("",gt_src_x,gt_src_y,1,gdalconst.GDT_Float32) #,['COMPRESS=LZW'] LZW is a lossless compression method achieve the highst compression but with lot of computation
        # set the geotransform
        dst.SetGeoTransform(gt_src_gt)
        # set the projection
        dst.SetProjection(gt_src_epsg.ExportToWkt())
        # set the no data value
        dst.GetRasterBand(1).SetNoDataValue(gt_src.GetRasterBand(1).GetNoDataValue())
        # initialize the band with the nodata value instead of 0
        dst.GetRasterBand(1).Fill(gt_src.GetRasterBand(1).GetNoDataValue())
        # perform the projection & resampling
        resample_technique = gdal.GRA_NearestNeighbour #gdal.GRA_NearestNeighbour

        # reproject the raster to the source projection
        ReprojectedRaster = gdal.Warp('', RasterTobeClippedPath,dstSRS='EPSG:'+gt_src_epsg.GetAttrValue('AUTHORITY',1),  format='VRT')

        gdal.ReprojectImage(ReprojectedRaster,dst,gt_src_epsg.ExportToWkt(),gt_src_epsg.ExportToWkt(),resample_technique)

        if Save:
            Raster.SaveRaster(dst,OutputPath)

        return dst


    @staticmethod
    def Mosaic(RasterList, Save=False, Path='MosaicedRaster.tif'):
        """


        Parameters
        ----------
        RasterList : [list]
            list of the raster files to mosaic.
        Save : [Bool], optional
            to save the clipped raster to your drive. The default is False.
        Path : [String], optional
            Path iincluding the extention (.tif). The default is 'MosaicedRaster.tif'.

        Returns
        -------
            1- Mosaiced raster: [Rasterio object]
                the whole mosaiced raster
            2-metadata : [dictionay]
                dictionary containing number of bands, coordinate reference system crs
                dtype, geotransform, height and width of the raster
        """
        # List for the source files
        RasterioObjects = []

        # Iterate over raster files and add them to source -list in 'read mode'
        for file in RasterList:
            src = rasterio.open(file)
            RasterioObjects.append(src)

        # Merge function returns a single mosaic array and the transformation info
        dst, dst_trans = rasterio.merge.merge(RasterioObjects)

        # Copy the metadata
        dst_meta = src.meta.copy()
        epsg_code = int(src.crs.data['init'][5:])
        # Update the metadata
        dst_meta.update({"driver": "GTiff",
                         "height": dst.shape[1],
                         "width": dst.shape[2],
                         "transform": dst_trans,
                         "crs": pyproj.CRS.from_epsg(epsg_code).to_wkt()
                         }
                        )

        if Save:
            # Write the mosaic raster to disk
            with rasterio.open(Path, "w", **dst_meta) as dest:
                dest.write(dst)

        return dst, dst_meta

    @staticmethod
    def ReadASCIIsFolder(path, pixel_type):
        """
        ===========================================================
           ReadASCIIsFolder(path, pixel_type)
        ===========================================================
        this function reads rasters from a folder and creates a 3d arraywith the same
        2d dimensions of the first raster in the folder and len as the number of files
        inside the folder.
        - all rasters should have the same dimensions
        - folder should only contain raster files

        Inputs:
        ----------
            1- path:
                [String] path of the folder that contains all the rasters.

        Outputs:
        ----------
            1- arr_3d:
                [numpy.ndarray] 3d array contains arrays read from all rasters in the folder.

            2-ASCIIDetails:
                [List] list of the six spatial information of the ASCII file
                [ASCIIRows, ASCIIColumns, XLowLeftCorner, YLowLeftCorner,
                CellSize, NoValue]
            3- files:
                [list] list of names of all files inside the folder

        Example:
        ----------
            path = "ASCII folder/"
            pixel_type = 1
            ASCIIArray, ASCIIDetails, NameList = ReadASCIIsFolder(path, pixel_type)

        """
        # input data validation
        # data type
        assert type(path)== str, "A_path input should be string type"
        # input values
        # check wether the path exist or not
        assert os.path.exists(path), "the path you have provided does not exist"
        # check whether there are files or not inside the folder
        assert os.listdir(path)!= "","the path you have provided is empty"
        # get list of all files
        files=os.listdir(path)
        if "desktop.ini" in files: files.remove("desktop.ini")
        # check that folder only contains rasters
        assert all(f.endswith(".asc") for f in files), "all files in the given folder should have .tif extension"
        # create a 3d array with the 2d dimension of the first raster and the len
        # of the number of rasters in the folder
        ASCIIValues, ASCIIDetails = Raster.ReadASCII(path+"/"+files[0], pixel_type)
        noval = ASCIIDetails[5]
        # fill the array with noval data
        arr_3d=np.ones((ASCIIDetails[0],ASCIIDetails[1],len(files)))*noval

        for i in range(len(files)):
            # read the tif file
            f,_ = Raster.ReadASCII(path+"/"+files[0], pixel_type)
            arr_3d[:,:,i]=f

        return arr_3d, ASCIIDetails, files


    def ASCIIFoldertoRaster(path,savePath,pixel_type=1,RasterFile = None,epsg = None):
        """
        =========================================================================
        ASCIItoRaster(path,savePath,pixel_type)
        =========================================================================

        This function takes the path of a folder contains ASCII files and convert
        them into a raster format and in takes  all the spatial information
        (projection, coordinates of the corner point), and number of rows
        and columns from raster file or you have to define the epsg corresponding
        to the you coordinate system and projection

        Inputs:
        =========

            1-path:
                [String] path to the folder containing the ASCII files

            2-savePath:
                [String] path to save the new raster including new raster name and extension (.tif)

            3-pixel_type:
                [Integer] type of the data to be stored in the pixels,default is 1 (float32)
                for example pixel type of flow direction raster is unsigned integer
                1 for float32
                2 for float64
                3 for Unsigned integer 16
                4 for Unsigned integer 32
                5 for integer 16
                6 for integer 32

            4-RasterFile:
                [String] source raster to get the spatial information, both ASCII
                file and source raster should have the same number of rows, and
                same number of columns default value is [None].

            5-epsg:
                EPSG stands for European Petroleum Survey Group and is an organization
                that maintains a geodetic parameter database with standard codes,
                the EPSG codes, for coordinate systems, datums, spheroids, units
                and such alike (https://epsg.io/) default value is [None].

        Outputs:
        =========
            1- a New Raster will be saved in the savePath containing the values
            of the ASCII file

        Example:
        =========
            1- ASCII to raster given a raster file:
                ASCIIFile = "soiltype.asc"
                RasterFile = "DEM.tif"
                savePath = "Soil_raster.tif"
                pixel_type = 1
                ASCIItoRaster(ASCIIFile,  savePath, pixel_type, RasterFile)
            2- ASCII to Raster given an EPSG number
                ASCIIFile = "soiltype.asc"
                savePath = "Soil_raster.tif"
                pixel_type = 1
                epsg = 4647
            ASCIIFoldertoRaster(path,savePath,pixel_type=5,epsg = epsg)
        """

        # input data validation
        # data type
        assert type(path)== str, "A_path input should be string type"
        # input values
        # check wether the path exist or not
        assert os.path.exists(path), "the path you have provided does not exist"
        # check whether there are files or not inside the folder
        assert os.listdir(path)!= "","the path you have provided is empty"
        # get list of all files
        files=os.listdir(path)
        if "desktop.ini" in files: files.remove("desktop.ini")
        # check that folder only contains rasters
        assert all(f.endswith(".asc") for f in files), "all files in the given folder should have .tif extension"
        # create a 3d array with the 2d dimension of the first raster and the len
        # of the number of rasters in the folder

        for i in range(len(files)):
                ASCIIFile = path + "/" + files[i]
                name = savePath + "/" + files[i].split(".")[0] + ".tif"
                Raster.ASCIItoRaster(ASCIIFile,name,pixel_type,RasterFile = None,epsg = epsg)


    @staticmethod
    def RastersLike(src,array,path=None):
        """
        ====================================================================
          RasterLike(src,array,path)
        ====================================================================
        this function creates a Geotiff raster like another input raster, new raster
        will have the same projection, coordinates or the top left corner of the original
        raster, cell size, nodata velue, and number of rows and columns
        the raster and the dem should have the same number of columns and rows

        inputs:
        ----------
            1- src:
                [gdal.dataset] source raster to get the spatial information
            2- array:
                [numpy array] 3D array to be stores as a rasters, the dimensions should be
                [rows, columns, timeseries length]
            3- path:
                [String] list of names to save the new rasters
                like ["results/surfaceDischarge_2012_08_13_23.tif","results/surfaceDischarge_2012_08_14_00.tif"]
                Default value is None

        outputs:
        ----------
            1- save the new raster to the given path

        Ex:
        ----------
            data
            src=gdal.Open("DEM.tif")
            name=["Q_2012_01_01_01.tif","Q_2012_01_01_02.tif","Q_2012_01_01_03.tif","Q_2012_01_01_04.tif"]
            RastersLike(src,data,name)

        """
        # input data validation
        # length of the 3rd dimension of the array
        try:
            l = np.shape(array)[2]
        except IndexError:
            assert False, "the array you have entered is 2D you have to use RasterLike function not RastersLike"

        # check length of the list of names to be equal to 3rd dimension of the array
        if path != None: # paths are given
            assert len(path) == np.shape(array)[2], "length of list of names " + str(len(path)) + "should equal the 3d dimension of the array-" + str(np.shape(array)[2])
        else: # paths are not given
            # try to create a folder called results at the current working directory to store resulted rasters
            try:
                os.makedirs(os.path.join(os.getcwd(),"result_rasters"))
            except WindowsError:
                assert False ,"please either to provide your own paths including folder name and rasternames.tif in a list or rename the folder called result_rasters"
            # careate list of names
            path = ["result_rasters/"+str(i)+".tif" for i in range(l)]

        for i in range(l):
            Raster.RasterLike(src,array[:,:,i],path[i])


    @staticmethod
    def MatchDataAlignment(A_path,B_input_path,new_B_path):
        """
        =========================================================================
          MatchData(A_path,B_input_path,new_B_path)
        =========================================================================
        this function matches the coordinate system and the number of of rows & columns
        between two rasters
        Raster A is the source of the coordinate system, no of rows and no of columns & cell size
        B_input_path is path to the folder where Raster B exist where  Raster B is
        the source of data values in cells
        the result will be a raster with the same structure like RasterA but with
        values from RasterB using Nearest Neighbour interpolation algorithm

        Inputs:
        ----------
            1- A_path:
                [String] path to the spatial information source raster to get the spatial information
                (coordinate system, no of rows & columns) A_path should include the name of the raster
                and the extension like "data/dem.tif"
            2- B_input_path:
                [String] path of the folder of the rasters (Raster B) you want to adjust their
                no of rows, columns and resolution (alignment) like raster A
                the folder should not have any other files except the rasters
            3- new_B_path:
                [String] [String] path where new rasters are going to be saved with exact
                same old names

        Outputs:
        ----------
            1- new rasters:
                ٌRasters have the values from rasters in B_input_path with the same
            cell size, no of rows & columns, coordinate system and alignment like raster A

        Example:
        ----------
            dem_path = "01GIS/inputs/4000/acc4000.tif"
            prec_in_path = "02Precipitation/CHIRPS/Daily/"
            prec_out_path = "02Precipitation/4km/"
            MatchData(dem_path,prec_in_path,prec_out_path)
        """
        # input data validation
        # data type
        assert type(A_path) == str, "A_path input should be string type"
        assert type(B_input_path) == str, "B_input_path input should be string type"
        assert type(new_B_path) == str, "new_B_path input should be string type"
        # input values
        ext = A_path[-4:]
        assert ext == ".tif", "please add the extension at the end of the path input"

        A = gdal.Open(A_path)
        files_list = os.listdir(B_input_path)
        if "desktop.ini" in files_list: files_list.remove("desktop.ini")

        print("New Path- " + new_B_path)
        for i in range(len(files_list)):
            print(str(i+1) + '/' + str(len(files_list)) + " - " + new_B_path+files_list[i])
            B = gdal.Open(B_input_path + files_list[i])
            new_B = Raster.MatchRasterAlignment(A,B)
            Raster.SaveRaster(new_B,new_B_path+files_list[i])

    @staticmethod
    def MatchDataNoValuecells(A_path,B_input_path,new_B_path):
        """
        ==============================================================
          MatchData(A_path,B_input_path,new_B_path)
        ==============================================================
        this function matches the location of nodata value from src raster to dst
        raster
        Raster A is where the NoDatavalue will be taken and the location of this value
        B_input_path is path to the folder where Raster B exist where  we need to put
        the NoDataValue of RasterA in RasterB at the same locations

        Inputs:
        ----------
            1- A_path:
                [String] path to the source raster to get the NoData value and it location in the array
                A_path should include the name of the raster and the extension like "data/dem.tif"
            2- B_input_path:
                [String] path of the folder of the rasters (Raster B) you want to set Nodata Value
                on the same location of NodataValue of Raster A, the folder should
                not have any other files except the rasters
            3- new_B_path:
                [String] [String] path where new rasters are going to be saved with exact
                same old names

        Outputs:
        ----------
            1- new rasters have the values from rasters in B_input_path with the NoDataValue in the same
            locations like raster A

        Example:
        ----------
            dem_path="01GIS/inputs/4000/acc4000.tif"
            temp_in_path="03Weather_Data/new/4km/temp/"
            temp_out_path="03Weather_Data/new/4km_f/temp/"
            MatchDataNoValuecells(dem_path,temp_in_path,temp_out_path)

        """
        # input data validation
        # data type
        assert type(A_path)== str, "A_path input should be string type"
        assert type(B_input_path)== str, "B_input_path input should be string type"
        assert type(new_B_path)== str, "new_B_path input should be string type"
        # input values
        ext=A_path[-4:]
        assert ext == ".tif", "please add the extension at the end of the path input"
        # check wether the path exists or not
        assert os.path.exists(A_path), "source raster you have provided does not exist"
        assert os.path.exists(B_input_path), B_input_path+" path you have provided does not exist"
        assert os.path.exists(new_B_path), new_B_path+" path you have provided does not exist"
        # check wether the folder has the rasters or not
        assert len(os.listdir(B_input_path)) > 0, B_input_path+" folder you have provided is empty"

        A=gdal.Open(A_path)
        files_list=os.listdir(B_input_path)
        if "desktop.ini" in files_list:  files_list.remove("desktop.ini")

        print("New Path- " + new_B_path)
        for i in range(len(files_list)):
            print(str(i+1) + '/' + str(len(files_list)) + " - " + new_B_path+files_list[i])
            B=gdal.Open(B_input_path+files_list[i])
            new_B=Raster.MatchNoDataValue(A,B)
            Raster.SaveRaster(new_B,new_B_path+files_list[i])


    @staticmethod
    def FolderCalculator(folder_path,new_folder_path,function):
        """
        =========================================================================
          FolderCalculator(folder_path, new_folder_path, function)
        =========================================================================
        this function matches the location of nodata value from src raster to dst
        raster
        Raster A is where the NoDatavalue will be taken and the location of this value
        B_input_path is path to the folder where Raster B exist where  we need to put
        the NoDataValue of RasterA in RasterB at the same locations

        Inputs:
        ----------
            1- folder_path:
                [String] path of the folder of rasters you want to execute a certain function on all
                of them
            2- new_folder_path:
                [String] path of the folder where resulted raster will be saved
            3- function:
                [function] callable function (builtin or user defined)

        Outputs:
        ----------
            1- new rasters will be saved to the new_folder_path

        Example:
        ----------
            def function(args):
                A = args[0]
                func=np.abs
                path = args[1]
                B=MapAlgebra(A,func)
                SaveRaster(B,path)

            folder_path = "03Weather_Data/new/4km_f/evap/"
            new_folder_path="03Weather_Data/new/4km_f/new_evap/"
            FolderCalculator(folder_path,new_folder_path,function)
        """
        # input data validation
        # data type
        assert type(folder_path)== str, "A_path input should be string type"
        assert type(new_folder_path)== str, "B_input_path input should be string type"
        assert callable(function) , "second argument should be a function"

        assert os.path.exists(folder_path), folder_path + "the path you have provided does not exist"
        assert os.path.exists(new_folder_path), new_folder_path + "the path you have provided does not exist"
        # check whether there are files or not inside the folder
        assert os.listdir(folder_path) != "", folder_path + "the path you have provided is empty"

        # check if you can create the folder
        # try:
        #     os.makedirs(os.path.join(os.environ['TEMP'],"AllignedRasters"))
        # except WindowsError :
        #     # if not able to create the folder delete the folder with the same name and create one empty
        #     shutil.rmtree(os.path.join(os.environ['TEMP']+"/AllignedRasters"))
        #     os.makedirs(os.path.join(os.environ['TEMP'],"AllignedRasters"))

        # get names of rasters
        files_list=os.listdir(folder_path)
        if "desktop.ini" in files_list: files_list.remove("desktop.ini")

        # execute the function on each raster
        for i in range(len(files_list)):
            print(str(i+1) + '/' + str(len(files_list)) + " - " + files_list[i])
            B=gdal.Open(folder_path+files_list[i])
            args=[B,new_folder_path+files_list[i]]
            function(args)

    @staticmethod
    def ReadRastersFolder(path,WithOrder=True):
        """
        ===========================================================
           ReadRastersFolder(path)
        ===========================================================
        this function reads rasters from a folder and creates a 3d arraywith the same
        2d dimensions of the first raster in the folder and len as the number of files
        inside the folder.
        - all rasters should have the same dimensions
        - folder should only contain raster files

        Inputs:
        ----------
            1- path:
                [String] path of the folder that contains all the rasters.

        Outputs:
        ----------
            1- arr_3d:
                [numpy.ndarray] 3d array contains arrays read from all rasters in the folder.

        Example:
        ----------
            prec_path="00inputs/meteodata/4000/prec"
            prec=ReadRastersFolder(prec_path)

        """
        # input data validation
        # data type
        assert type(path)== str or type(path) == list, "A_path input should be string type"

        # input values
        if type(path)== str:
            # check wether the path exist or not
            assert os.path.exists(path), "the path you have provided does not exist"
            # check whether there are files or not inside the folder
            assert os.listdir(path)!= "","the path you have provided is empty"
            # get list of all files
            files = os.listdir(path)
            if "desktop.ini" in files: files.remove("desktop.ini")
        else:
            files = path[:]

        # to sort the files in the same order as the first number in the name
        if WithOrder == True:
            try:
                filesNo = [int(files[i].split("_")[0]) for i in range(len(files))]
            except:
                ErrorMsg = """please include a number at the beginning of the
                rasters name to indicate the order of the raster please use the
                Inputs.RenameFiles method to solve this issue and don't include
                any other files in the folder with the rasters"""
                assert False, ErrorMsg


            filetuple = sorted(zip(filesNo, files))
            files = [x for _,x in filetuple]


        # check that folder only contains rasters
        assert all(f.endswith(".tif") for f in files), "all files in the given folder should have .tif extension"
        # create a 3d array with the 2d dimension of the first raster and the len
        # of the number of rasters in the folder
        if type(path) == list:
            sample = gdal.Open(files[0])
        else:
            sample = gdal.Open(path+"/"+files[0])

        dim = sample.ReadAsArray().shape
        naval = sample.GetRasterBand(1).GetNoDataValue()
        # fill the array with noval data
        arr_3d = np.ones((dim[0],dim[1],len(files)))
        arr_3d [:,:,:] = naval

        if type(path) == list:
            for i in range(len(files)):
                # read the tif file
                f = gdal.Open(files[i])
                arr_3d[:,:,i] = f.ReadAsArray()
        else:
            for i in range(len(files)):
                # read the tif file
                f = gdal.Open(path+"/"+files[i])
                arr_3d[:,:,i] = f.ReadAsArray()

        return arr_3d


    def ExtractValues(Path, ExcludeValue, Compressed = True, OccupiedCellsOnly=True):
        """
        =================================================================
            ExtractValues(Path, ExcludeValue, Compressed = True)
        =================================================================
        this function is written to extract and return a list of all the values
        in a map
        #TODO (an ASCII for now to be extended later to read also raster)
        Inputs:
            1-Path
                [String] a path includng the name of the ASCII and extention like
                path="data/cropped.asc"
            2-ExcludedValue:
                [Numeric] values you want to exclude from exteacted values
            3-Compressed:
                [Bool] if the map you provided is compressed
        """
        # input data validation
        # data type
        assert type(Path)== str, "Path input should be string type" + str(Path)
        assert type(Compressed) == bool, "Compressed input should be Boolen type"
        # input values
        # check wether the path exist or not
        assert os.path.exists(Path), "the path you have provided does not exist"
        # check wether the path has the extention or not
        if Compressed == True:
            assert Path.endswith(".zip") , "file" + Path +" should have .asc extension"
        else:
            assert Path.endswith(".asc") , "file" + Path +" should have .asc extension"


        ExtractedValues = list()


        try:
            # open the zip file
            if Compressed :
                Compressedfile = zipfile.ZipFile(Path)
                # get the file name
                fname = Compressedfile.infolist()[0]
                # ASCIIF = Compressedfile.open(fname)
                # SpatialRef = ASCIIF.readlines()[:6]
                ASCIIF = Compressedfile.open(fname)
                ASCIIRaw = ASCIIF.readlines()[6:]
                rows = len(ASCIIRaw)
                cols = len(ASCIIRaw[0].split())
                MapValues = np.ones((rows,cols), dtype = np.float32)*0
                # read the ascii file
                for i in range(rows):
                    x = ASCIIRaw[i].split()
                    MapValues[i,:] = list(map(float, x ))

            else:
                MapValues, SpatialRef= Raster.ReadASCII(Path)

            # count nonzero cells
            NonZeroCells = np.count_nonzero(MapValues)

            if OccupiedCellsOnly == True:
                ExtractedValues = 0
                return ExtractedValues, NonZeroCells

            # get the position of cells that is not zeros
            rows = np.where(MapValues[:,:] != ExcludeValue)[0]
            cols = np.where(MapValues[:,:] != ExcludeValue)[1]

        except:
            print("Error Opening the compressed file")
            NonZeroCells = -1
            ExtractedValues = -1
            return ExtractedValues, NonZeroCells


        # get the values of the filtered cells
        for i in range(len(rows)):
            ExtractedValues.append(MapValues[rows[i],cols[i]])

        return ExtractedValues, NonZeroCells


    @staticmethod
    def OverlayMap(Path, BaseMap, ExcludeValue, Compressed = False, OccupiedCellsOnly=True):
        """
        =================================================================
            (Path, BaseMap, ExcludeValue, Compressed = False, OccupiedCellsOnly=True)
        =================================================================
        this function is written to extract and return a list of all the values
        in an ASCII file

        Inputs:
            1-Path:
                [String] a path to ascii file (inclusing the extension).
            2-BaseMap:
                [String/array] a path includng the name of the ASCII and extention like
                path="data/cropped.asc".
            3-ExcludedValue:
                [Numeric] values you want to exclude from extracted values.
            4-Compressed:
                [Bool] if the map you provided is compressed.
            5-OccupiedCellsOnly:
                [Bool] if you want to count only cells that is not zero.
        Outputs:
            1- ExtractedValues:
                [Dict] dictonary with a list of values in the basemap as keys
                    and for each key a list of all the intersected values in the
                    maps from the path.
            2- NonZeroCells:
                [dataframe] dataframe with the first column as the "file" name
                and the second column is the number of cells in each map.
        """
        # input data validation
        # data type
        assert type(Path)== str, "Path input should be string type"
        assert type(Compressed) == bool, "Compressed input should be Boolen type"
        # assert type(BaseMapF) == str, "BaseMapF input should be string type"
        # input values
        # check wether the path exist or not
        assert os.path.exists(Path), "the path you have provided does not exist"




        # read the base map
        if type(BaseMap) == str:
            if BaseMap.endswith('.asc'):
                BaseMapV, _ = Raster.ReadASCII(BaseMap)
            else:
                BaseMap = gdal.Open(BaseMap)
                BaseMapV = BaseMap.ReadAsArray()
        else:
            BaseMapV = BaseMap

        ExtractedValues = dict()

        try:
            # open the zip file
            if Compressed :
                Compressedfile = zipfile.ZipFile(Path)
                # get the file name
                fname = Compressedfile.infolist()[0]
                ASCIIF = Compressedfile.open(fname)
    #                SpatialRef = ASCIIF.readlines()[:6]
                ASCIIF = Compressedfile.open(fname)
                ASCIIRaw = ASCIIF.readlines()[6:]
                rows = len(ASCIIRaw)
                cols = len(ASCIIRaw[0].split())
                MapValues = np.ones((rows,cols), dtype = np.float32)*0
                # read the ascii file
                for row in range(rows):
                    x = ASCIIRaw[row].split()
                    MapValues[row,:] = list(map(float, x ))

            else:
                MapValues, SpatialRef= Raster.ReadASCII(Path)
            # count number of nonzero cells
            NonZeroCells = np.count_nonzero(MapValues)

            if OccupiedCellsOnly == True:
                ExtractedValues = 0
                return ExtractedValues, NonZeroCells

            # get the position of cells that is not zeros
            rows = np.where(MapValues[:,:] != ExcludeValue)[0]
            cols = np.where(MapValues[:,:] != ExcludeValue)[1]


        except:
            print("Error Opening the compressed file")
            NonZeroCells = -1
            ExtractedValues = -1
            return ExtractedValues, NonZeroCells

        # extract values
        for i in range(len(rows)):
            # first check if the sub-basin has a list in the dict if not create a list
            if BaseMapV[rows[i],cols[i]] not in list(ExtractedValues.keys()):
                ExtractedValues[BaseMapV[rows[i],cols[i]]] = list()

    #            if not np.isnan(MapValues[rows[i],cols[i]]):
            ExtractedValues[BaseMapV[rows[i],cols[i]]].append(MapValues[rows[i],cols[i]])
    #            else:
                # if the value is nan
    #                NanList.append(FilteredList[i])

        return ExtractedValues, NonZeroCells

    @staticmethod
    def OverlayMaps(Path, BaseMapF, FilePrefix, ExcludeValue, Compressed = False,
                    OccupiedCellsOnly=True):
        """
        =================================================================
            OverlayMaps(Path, ExcludeValue, Compressed = True)
        =================================================================
        this function is written to extract and return a list of all the values
        in an ASCII file

        Inputs:
            1-Path
                [String] a path to the folder includng the maps.
            2-BaseMapF:
                [String] a path includng the name of the ASCII and extention like
                path="data/cropped.asc"
            3-FilePrefix:
                [String] a string that make the files you want to filter in the folder
                uniq
            3-ExcludedValue:
                [Numeric] values you want to exclude from exteacted values
            4-Compressed:
                [Bool] if the map you provided is compressed
            5-OccupiedCellsOnly:
                [Bool] if you want to count only cells that is not zero
        Outputs:
            1- ExtractedValues:
                [Dict] dictonary with a list of values in the basemap as keys
                    and for each key a list of all the intersected values in the
                    maps from the path
            2- NonZeroCells:
                [dataframe] dataframe with the first column as the "file" name
                and the second column is the number of cells in each map
        """
        # input data validation
        # data type
        assert type(Path)== str, "Path input should be string type"
        assert type(FilePrefix)== str, "Path input should be string type"
        assert type(Compressed) == bool, "Compressed input should be Boolen type"
        assert type(BaseMapF) == str, "BaseMapF input should be string type"
        # input values
        # check wether the path exist or not
        assert os.path.exists(Path), "the path you have provided does not exist"
        # check whether there are files or not inside the folder
        assert os.listdir(Path)!= "","the path you have provided is empty"
        # get list of all files
        Files=os.listdir(Path)

        FilteredList = list()

        # filter file list with the File prefix input
        for i in range(len(Files)):
            if Files[i].startswith(FilePrefix):
                FilteredList.append(Files[i])

        NonZeroCells = pd.DataFrame()
        NonZeroCells['files'] = FilteredList
        NonZeroCells['cells'] = 0
        # read the base map
        if BaseMapF.endswith('.asc'):
            BaseMapV, _ = Raster.ReadASCII(BaseMapF)
        else:
            BaseMap = gdal.Open(BaseMapF)
            BaseMapV = BaseMap.ReadAsArray()

        ExtractedValues = dict()
        FilesNotOpened = list()

        for i in range(len(FilteredList)):
            print("File " + FilteredList[i])
            if OccupiedCellsOnly == True :
                ExtractedValuesi , NonZeroCells.loc[i,'cells'] = Raster.OverlayMap(Path + "/" + FilteredList[i],
                                                                      BaseMapV, ExcludeValue, Compressed,
                                                                      OccupiedCellsOnly)
            else:
                ExtractedValuesi, NonZeroCells.loc[i,'cells'] = Raster.OverlayMap(Path + "/" + FilteredList[i],
                                                                      BaseMapV, ExcludeValue, Compressed,
                                                                      OccupiedCellsOnly)

                # these are the destinct values from the BaseMap which are keys in the
                # ExtractedValuesi dict with each one having a list of values
                BaseMapValues = list(ExtractedValuesi.keys())

                for j in range(len(BaseMapValues)):
                    if BaseMapValues[j] not in list(ExtractedValues.keys()):
                        ExtractedValues[BaseMapValues[j]] = list()

                    ExtractedValues[BaseMapValues[j]] = ExtractedValues[BaseMapValues[j]] + ExtractedValuesi[BaseMapValues[j]]

            if ExtractedValuesi == -1 or NonZeroCells.loc[i,'cells'] == -1:
                FilesNotOpened.append(FilteredList[i])
                continue

        return ExtractedValues, NonZeroCells


    @staticmethod
    def Normalize(array):
        """
        Normalizes numpy arrays into scale 0.0 - 1.0

        Parameters
        ----------
        array : TYPE
            DESCRIPTION.

        Returns
        -------
        TYPE
            DESCRIPTION.

        """

        array_min, array_max = array.min(), array.max()
        return ((array - array_min)/(array_max - array_min))

    @staticmethod
    def GetEpsg(proj, extension = 'tiff'):
        """
        =====================================================
            GetEpsg(proj, extension = 'tiff')
        =====================================================
        This function reads the projection of a GEOGCS file or tiff file

        Parameters
        ----------
        proj : TYPE
            projection read from the netcdf file.
        extension : [string], optional
            tiff or GEOGCS . The default is 'tiff'.

        Returns
        -------
        epsg : [integer]
            epsg number
        """
        try:
            if extension == 'tiff':
                # Get info of the dataset that is used for transforming
                g_proj = proj.GetProjection()
                Projection=g_proj.split('EPSG","')
            if extension == 'GEOGCS':
                Projection = proj
            epsg = int((str(Projection[-1]).split(']')[0])[0:-1])
        except:
           epsg = 4326

        return(epsg)

    @staticmethod
    def NCdetails(nc, Var = None):
        """
        ==========================================================
            NCGetGeotransform(nc, Var = None)
        ==========================================================
        NCGetGeotransform takes a netcdf object and return the geottansform data of
        the bottom left corner

        Parameters
        ----------
        nc : [netcdf object]
            netcdf object .
        Var : [string], optional
            the variable you want to read from the netcdf file if None is given the
            last variable in the file will be read. The default is None.

        Returns
        -------
        1-geo : [tuple]
            geotransform data of the netcdf file
        2-epsg : [integer]
            epsg number
        3-size_X : [integer]
            number of coordinates in x direction
        4-size_Y : [integer]
            number of coordinates in y direction
        5-size_Z : [integer]
            number of coordinates in z direction
        6-Time : [integer]
            time varialble in the netcdf file
        """
        # list if variables
        if Var is None:
            Var = list(nc.variables.keys())[-1]

        data = nc.variables[Var]
        # nodatavalue
        try:
            NoDataValue = data._FillValue
        except AttributeError:
            NoDataValue = data.missing_value
        # data type
        try:
            datatype = data.datatype
        except AttributeError:
            datatype = data.dtype

        size_Y, size_X = np.int_(data.shape[-2:])
        # if there is a stack of layers in the file (3d array)
        if len(data.shape) == 3 and data.shape[0] > 1 :
            size_Z = np.int_(data.shape[0])
            try:
                TimeVar = nc.variables['time']
                Time = TimeVar[:]
                # convert  time numbers to dates
                Time = netCDF4.num2date(Time[:],TimeVar.units)
            except:
                Time = nc.variables['t'][:]
                # Time = nc.variables['t'].units[11:]
        else:
            # if there is only one layer(2D array)
            size_Z = 1
            Time = -9999

        # get lats and lons
        try:
            lats = nc.variables['latitude'][:]
            # Geo6 = nc.variables['latitude'].res
        except:
            lats = nc.variables['lat'][:]
            # Geo6 = nc.variables['lat'].res


        try:
            lons = nc.variables['longitude'][:]

        except:
            lons = nc.variables['lon'][:]
            # Geo2 = nc.variables['lon'].size

        # try to get the resolutio of the file
        try:
            try:
                Geo2 = nc.variables['longitude'].res
            except:
                try:
                    Geo2 = nc.variables['lon'].res
                except:
                    Geo2 = lons[1] - lons[0]
        except:
            assert False, "the netcdf file does not hae a resolution attribute"


        # Lower left corner corner coordinates
        Geo4 = np.min(lats) + Geo2/2
        Geo1 = np.min(lons) - Geo2/2

        try:
            crso = nc.variables['crs']
            proj = crso.projection
            epsg = Raster.GetEpsg(proj, extension = 'GEOGCS')
        except:
            epsg = 4326

        geo = tuple([Geo1, Geo2, 0, Geo4, 0, Geo2])

        return geo, epsg, size_X, size_Y, size_Z, Time, NoDataValue, datatype

    @staticmethod
    def NCtoTiff(input_nc, SaveTo, Separator='_'):
        """
        =========================================================
           NCtoTiff(input_nc, SaveTo)
        =========================================================

        Parameters
        ----------
        input_nc : [string/list]
            a path of the netcdf file of a list of the netcdf files' names.
        SaveTo : TYPE
            Path to where you want to save the files.
        Separator : [string]
            separator in the file name that separate the name from the date.
            Default is "_"
        Returns
        -------
        None.

        """
        if type(input_nc) == str:
            nc = netCDF4.Dataset(input_nc)
        elif type(input_nc) == list:
            nc = netCDF4.MFDataset(input_nc)

        # get the variable
        Var = list(nc.variables.keys())[-1]
        # extract the data
        All_Data = nc[Var]
        # get the details of the file
        geo, epsg, size_X, size_Y, size_Z, Time, NoDataValue, datatype = Raster.NCdetails(nc)

        # Create output folder if needed
        if not os.path.exists(SaveTo):
            os.mkdir(SaveTo)

        for i in range(0,size_Z):
            if All_Data.shape[0] and All_Data.shape[0] > 1 :#type(Time) == np.ndarray: #not Time == -9999
                time_one = Time[i]
                # d = dt.date.fromordinal(int(time_one))
                name = os.path.splitext(os.path.basename(input_nc))[0]
                nameparts = name.split(Separator)[0] # [0:-2]
                name_out = os.path.join(SaveTo + "/" + nameparts + '_%d.%02d.%02d.tif' %(time_one.year, time_one.month, time_one.day))
                data = All_Data[i,:,:]
            else:
                name=os.path.splitext(os.path.basename(input_nc))[0]
                name_out = os.path.join(SaveTo, name + '.tif')
                data = All_Data[0,:,:]

            driver = gdal.GetDriverByName("GTiff")
            # driver = gdal.GetDriverByName("MEM")

            if datatype == np.float32:
                dst = driver.Create(name_out,int(data.shape[1]), int(data.shape[0]), 1,
                                   gdal.GDT_Float32, ['COMPRESS=LZW'])
            elif datatype == np.float64:
                dst = driver.Create(name_out,int(data.shape[1]), int(data.shape[0]), 1,
                                   gdal.GDT_Float64)
            elif datatype == np.uint16:
                dst = driver.Create(name_out,int(data.shape[1]), int(data.shape[0]), 1,
                                   gdal.GDT_UInt16, ['COMPRESS=LZW'])
            elif datatype == np.uint32:
                dst = driver.Create(name_out,int(data.shape[1]), int(data.shape[0]), 1,
                                   gdal.GDT_UInt32, ['COMPRESS=LZW'])
            elif datatype == np.int16:
                dst = driver.Create(name_out,int(data.shape[1]), int(data.shape[0]), 1,
                                   gdal.GDT_Int16, ['COMPRESS=LZW'])
            elif datatype == np.int32:
                dst = driver.Create(name_out,int(data.shape[1]), int(data.shape[0]), 1,
                                   gdal.GDT_Int32, ['COMPRESS=LZW'])

            srse = osr.SpatialReference()
            if epsg == '':
                srse.SetWellKnownGeogCS("WGS84")

            else:
                try:
                    if not srse.SetWellKnownGeogCS(epsg) == 6:
                        srse.SetWellKnownGeogCS(epsg)
                    else:
                        try:
                            srse.ImportFromEPSG(int(epsg))
                        except:
                            srse.ImportFromWkt(epsg)
                except:
                    try:
                        srse.ImportFromEPSG(int(epsg))
                    except:
                        srse.ImportFromWkt(epsg)

            # set the geotransform
            dst.SetGeoTransform(geo)
            # set the projection
            dst.SetProjection(srse.ExportToWkt())
            # setting the NoDataValue does not accept double precision numbers
            try:
                dst.GetRasterBand(1).SetNoDataValue(NoDataValue)
                # initialize the band with the nodata value instead of 0
                dst.GetRasterBand(1).Fill(NoDataValue)
            except:
                NoDataValue = -9999
                dst.GetRasterBand(1).SetNoDataValue(NoDataValue)
                dst.GetRasterBand(1).Fill(NoDataValue)
                # assert False, "please change the NoDataValue in the source raster as it is not accepted by Gdal"
                print("the NoDataValue in the source Netcdf is double precission and as it is not accepted by Gdal")
                print("the NoDataValue now is et to -9999 in the raster")

            dst.GetRasterBand(1).WriteArray(data)
            dst.FlushCache()
            dst = None

    def Convert_nc_to_tiff(input_nc, output_folder):
        """
        This function converts the nc file into tiff files

        Keyword Arguments:
        input_nc -- name, name of the adf file
        output_folder -- Name of the output tiff file
        """

        #All_Data = Raster.Open_nc_array(input_nc)

        if type(input_nc) == str:
            nc = netCDF4.Dataset(input_nc)
        elif type(input_nc) == list:
            nc = netCDF4.MFDataset(input_nc)

        Var = nc.variables.keys()[-1]
        All_Data = nc[Var]

        geo_out, epsg, size_X, size_Y, size_Z, Time = Raster.Open_nc_info(input_nc)

        if epsg == 4326:
            epsg = 'WGS84'

        # Create output folder if needed
        if not os.path.exists(output_folder):
            os.mkdir(output_folder)

        for i in range(0,size_Z):
            if not Time == -9999:
                time_one = Time[i]
                d = dt.fromordinal(time_one)
                name = os.path.splitext(os.path.basename(input_nc))[0]
                nameparts = name.split('_')[0:-2]
                name_out = os.path.join(output_folder, '_'.join(nameparts) + '_%d.%02d.%02d.tif' %(d.year, d.month, d.day))
                Data_one = All_Data[i,:,:]
            else:
                name=os.path.splitext(os.path.basename(input_nc))[0]
                name_out = os.path.join(output_folder, name + '.tif')
                Data_one = All_Data[:,:]

            Raster.CreateRaster(name_out, Data_one, geo_out, epsg)

        return()


    def Convert_grb2_to_nc(input_wgrib, output_nc, band):



        # Get environmental variable
        WA_env_paths = os.environ["WA_PATHS"].split(';')
        GDAL_env_path = WA_env_paths[0]
        GDAL_TRANSLATE_PATH = os.path.join(GDAL_env_path, 'gdal_translate.exe')

        # Create command
        fullCmd = ' '.join(['"%s" -of netcdf -b %d' %(GDAL_TRANSLATE_PATH, band), input_wgrib, output_nc])  # -r {nearest}

        Raster.Run_command_window(fullCmd)

        return()

    def Convert_adf_to_tiff(input_adf, output_tiff):
        """
        This function converts the adf files into tiff files

        Keyword Arguments:
        input_adf -- name, name of the adf file
        output_tiff -- Name of the output tiff file
        """

        # Get environmental variable
        WA_env_paths = os.environ["WA_PATHS"].split(';')
        GDAL_env_path = WA_env_paths[0]
        GDAL_TRANSLATE_PATH = os.path.join(GDAL_env_path, 'gdal_translate.exe')

        # convert data from ESRI GRID to GeoTIFF
        fullCmd = ('"%s" -co COMPRESS=DEFLATE -co PREDICTOR=1 -co '
                       'ZLEVEL=1 -of GTiff %s %s') % (GDAL_TRANSLATE_PATH, input_adf, output_tiff)

        Raster.Run_command_window(fullCmd)

        return(output_tiff)

    def Convert_bil_to_tiff(input_bil, output_tiff):
        """
        This function converts the bil files into tiff files

        Keyword Arguments:
        input_bil -- name, name of the bil file
        output_tiff -- Name of the output tiff file
        """


        gdal.GetDriverByName('EHdr').Register()
        dest = gdal.Open(input_bil, gdalconst.GA_ReadOnly)
        Array = dest.GetRasterBand(1).ReadAsArray()
        geo_out = dest.GetGeoTransform()
        Raster.CreateRaster(output_tiff, Array, geo_out, "WGS84")

        return(output_tiff)


    def Convert_hdf5_to_tiff(inputname_hdf, Filename_tiff_end, Band_number, scaling_factor, geo_out):
        """
        This function converts the hdf5 files into tiff files

        Keyword Arguments:
        input_adf -- name, name of the adf file
        output_tiff -- Name of the output tiff file
        Band_number -- bandnumber of the hdf5 that needs to be converted
        scaling_factor -- factor multipied by data is the output array
        geo -- [minimum lon, pixelsize, rotation, maximum lat, rotation,
                pixelsize], (geospatial dataset)
        """

        # Open the hdf file
        g = gdal.Open(inputname_hdf, gdal.GA_ReadOnly)

        #  Define temporary file out and band name in
        name_in = g.GetSubDatasets()[Band_number][0]

        # Get environmental variable
        WA_env_paths = os.environ["WA_PATHS"].split(';')
        GDAL_env_path = WA_env_paths[0]
        GDAL_TRANSLATE = os.path.join(GDAL_env_path, 'gdal_translate.exe')

        # run gdal translate command
        FullCmd = '%s -of GTiff %s %s' %(GDAL_TRANSLATE, name_in, Filename_tiff_end)
        Raster.Run_command_window(FullCmd)

        # Get the data array
        dest = gdal.Open(Filename_tiff_end)
        Data = dest.GetRasterBand(1).ReadAsArray()
        dest = None

        # If the band data is not SM change the DN values into PROBA-V values and write into the spectral_reflectance_PROBAV
        Data_scaled = Data * scaling_factor

        # Save the PROBA-V as a tif file
        Raster.CreateRaster(Filename_tiff_end, Data_scaled, geo_out, "WGS84")

        return()

    # def Extract_Data(input_file, output_folder):
    #     """
    #     This function extract the zip files

    #     Keyword Arguments:
    #     output_file -- name, name of the file that must be unzipped
    #     output_folder -- Dir, directory where the unzipped data must be
    #                            stored
    #     """
    #     # extract the data
    #     z = zipfile.ZipFile(input_file, 'r')
    #     z.extractall(output_folder)
    #     z.close()

    @staticmethod
    def ExtractFromGZ(InputFile, OutputFile, delete=False):
        """
        ============================================================
             ExtractFromGZ(zip_filename, outfilename)
        ============================================================

        ExtractFromGZ method extract data from the zip/.gz files,
        save the data

        Parameters
        ----------
        zip_filename : [str]
            zipped file name .
        outfilename : [str]
            directory where the unzipped data must be
                                stored.
        delete : [bool]
            True if you want to delete the zipped file after the extracting the data
        Returns
        -------
        None.

        """
        with gzip.GzipFile(InputFile, 'rb') as zf:
            content = zf.read()
            save_file_content = open(OutputFile, 'wb')
            save_file_content.write(content)

        save_file_content.close()
        zf.close()

        if delete:
            os.remove(InputFile)

    # def Extract_Data_tar_gz(zip_filename, output_folder):
    #     """
    #     This function extract the tar.gz files

    #     Keyword Arguments:
    #     zip_filename -- name, name of the file that must be unzipped
    #     output_folder -- Dir, directory where the unzipped data must be
    #                            stored
    #     """

    #     os.chdir(output_folder)
    #     tar = tarfile.open(zip_filename, "r:gz")
    #     tar.extractall()
    #     tar.close()


    def SaveNC(namenc, DataCube, Var, Reference_filename,  Startdate = '', Enddate = '', Time_steps = '', Scaling_factor = 1):
        """
        Save_as_NC(namenc, DataCube, Var, Reference_filename,  Startdate = '',
                   Enddate = '', Time_steps = '', Scaling_factor = 1)




        Parameters
        ----------
        namenc : [str]
            complete path of the output file with .nc extension.
        DataCube : [array]
            dataset of the nc file, can be a 2D or 3D array [time, lat, lon],
            must be same size as reference data.
        Var : [str]
            the name of the variable.
        Reference_filename : [str]
            complete path to the reference file name.
        Startdate : str, optional
            needs to be filled when you want to save a 3D array,'YYYY-mm-dd'
            defines the Start datum of the dataset. The default is ''.
        Enddate : str, optional
            needs to be filled when you want to save a 3D array, 'YYYY-mm-dd'
            defines the End datum of the dataset. The default is ''.
        Time_steps : str, optional
            'monthly' or 'daily', needs to be filled when you want to save a
            3D array, defines the timestep of the dataset. The default is ''.
        Scaling_factor : TYPE, optional
            number, scaling_factor of the dataset. The default is 1.

        Returns
        -------
        None.

        """

        if not os.path.exists(namenc):

            # Get raster information
            geo_out, proj, size_X, size_Y = Raster.Open_array_info(Reference_filename)

            # Create the lat/lon rasters
            lon = np.arange(size_X)*geo_out[1]+geo_out[0] - 0.5 * geo_out[1]
            lat = np.arange(size_Y)*geo_out[5]+geo_out[3] - 0.5 * geo_out[5]

            # Create the nc file
            nco = netCDF4.Dataset(namenc, 'w', format='NETCDF4_CLASSIC')
            nco.description = '%s data' %Var

            # Create dimensions, variables and attributes:
            nco.createDimension('longitude', size_X)
            nco.createDimension('latitude', size_Y)

            # Create time dimension if the parameter is time dependent
            if Startdate != '':
                if Time_steps == 'monthly':
                    Dates = pd.date_range(Startdate,Enddate,freq = 'MS')
                if Time_steps == 'daily':
                    Dates = pd.date_range(Startdate,Enddate,freq = 'D')
                time_or=np.zeros(len(Dates))
                i = 0
                for Date in Dates:
                    time_or[i] = Date.toordinal()
                    i += 1
                nco.createDimension('time', None)
                timeo = nco.createVariable('time', 'f4', ('time',))
                timeo.units = '%s' %Time_steps
                timeo.standard_name = 'time'

            # Create the lon variable
            lono = nco.createVariable('longitude', 'f8', ('longitude',))
            lono.standard_name = 'longitude'
            lono.units = 'degrees_east'
            lono.pixel_size = geo_out[1]

            # Create the lat variable
            lato = nco.createVariable('latitude', 'f8', ('latitude',))
            lato.standard_name = 'latitude'
            lato.units = 'degrees_north'
            lato.pixel_size = geo_out[5]

            # Create container variable for CRS: lon/lat WGS84 datum
            crso = nco.createVariable('crs', 'i4')
            crso.long_name = 'Lon/Lat Coords in WGS84'
            crso.grid_mapping_name = 'latitude_longitude'
            crso.projection = proj
            crso.longitude_of_prime_meridian = 0.0
            crso.semi_major_axis = 6378137.0
            crso.inverse_flattening = 298.257223563
            crso.geo_reference = geo_out

            # Create the data variable
            if Startdate != '':
                preco = nco.createVariable('%s' %Var, 'f8',  ('time', 'latitude', 'longitude'), zlib=True, least_significant_digit=1)
                timeo[:]=time_or
            else:
                preco = nco.createVariable('%s' %Var, 'f8',  ('latitude', 'longitude'), zlib=True, least_significant_digit=1)

            # Set the data variable information
            preco.scale_factor = Scaling_factor
            preco.add_offset = 0.00
            preco.grid_mapping = 'crs'
            preco.set_auto_maskandscale(False)

            # Set the lat/lon variable
            lono[:] = lon
            lato[:] = lat

            # Set the data variable
            if Startdate != '':
                for i in range(len(Dates)):
                    preco[i,:,:] = DataCube[i,:,:]*1./np.float(Scaling_factor)
            else:
                preco[:,:] = DataCube[:,:] * 1./np.float(Scaling_factor)

            nco.close()
        return()

    def Create_NC_name(Var, Simulation, Dir_Basin, sheet_nmbr, info = ''):

        # Create the output name
        nameOut=''.join(['_'.join([Var,'Simulation%d' % Simulation,'_'.join(info)]),'.nc'])
        namePath = os.path.join(Dir_Basin,'Simulations','Simulation_%d' %Simulation, 'Sheet_%d' %sheet_nmbr)
        if not os.path.exists(namePath):
            os.makedirs(namePath)
        nameTot=os.path.join(namePath,nameOut)

        return(nameTot)

    def Create_new_NC_file(nc_outname, Basin_Example_File, Basin):

        # Open basin file
        dest = gdal.Open(Basin_Example_File)
        Basin_array = dest.GetRasterBand(1).ReadAsArray()
        Basin_array[np.isnan(Basin_array)] = -9999
        Basin_array[Basin_array<0] = -9999

        # Get Basic information
        Geo = dest.GetGeoTransform()
        size_X = dest.RasterXSize
        size_Y = dest.RasterYSize
        epsg = dest.GetProjection()

        # Get Year and months
        year = int(os.path.basename(nc_outname).split(".")[0])
        Dates = pd.date_range("%d-01-01" %year, "%d-12-31" %year, freq = "MS")

        # Latitude and longitude
        lons = np.arange(size_X)*Geo[1]+Geo[0] + 0.5 * Geo[1]
        lats = np.arange(size_Y)*Geo[5]+Geo[3] + 0.5 * Geo[5]

        # Create NetCDF file
        nco = netCDF4.Dataset(nc_outname, 'w', format = 'NETCDF4_CLASSIC')
        nco.set_fill_on()
        nco.description = '%s' %Basin

        # Create dimensions
        nco.createDimension('latitude', size_Y)
        nco.createDimension('longitude', size_X)
        nco.createDimension('time', None)

        # Create NetCDF variables
        crso = nco.createVariable('crs', 'i4')
        crso.long_name = 'Lon/Lat Coords in WGS84'
        crso.standard_name = 'crs'
        crso.grid_mapping_name = 'latitude_longitude'
        crso.projection = epsg
        crso.longitude_of_prime_meridian = 0.0
        crso.semi_major_axis = 6378137.0
        crso.inverse_flattening = 298.257223563
        crso.geo_reference = Geo

        ######################### Save Rasters in NetCDF ##############################

        lato = nco.createVariable('latitude', 'f8', ('latitude',))
        lato.units = 'degrees_north'
        lato.standard_name = 'latitude'
        lato.pixel_size = Geo[5]

        lono = nco.createVariable('longitude', 'f8', ('longitude',))
        lono.units = 'degrees_east'
        lono.standard_name = 'longitude'
        lono.pixel_size = Geo[1]

        timeo = nco.createVariable('time', 'f4', ('time',))
        timeo.units = 'Monthly'
        timeo.standard_name = 'time'

        # Variables
        basin_var = nco.createVariable('Landuse', 'i',
                                               ('latitude', 'longitude'),
                                               fill_value=-9999)
        basin_var.long_name = 'Landuse'
        basin_var.grid_mapping = 'crs'

        # Create time unit
        i = 0
        time_or=np.zeros(len(Dates))
        for Date in Dates:
            time_or[i] = Date.toordinal()
            i += 1

        # Load data
        lato[:] = lats
        lono[:] = lons
        timeo[:] = time_or
        basin_var[:,:] = Basin_array

        # close the file
        time.sleep(1)
        nco.close()
        return()

    def Add_NC_Array_Variable(nc_outname, Array, name, unit, Scaling_factor = 1):

        # create input array
        Array[np.isnan(Array)] = -9999 * np.float(Scaling_factor)
        Array = np.int_(Array * 1./np.float(Scaling_factor))

        # Create NetCDF file
        nco = netCDF4.Dataset(nc_outname, 'r+', format = 'NETCDF4_CLASSIC')
        nco.set_fill_on()

        paro = nco.createVariable('%s' %name, 'i',
                                       ('time', 'latitude', 'longitude'),fill_value=-9999,
                                        zlib=True, least_significant_digit=0)

        paro.scale_factor = Scaling_factor
        paro.add_offset = 0.00
        paro.grid_mapping = 'crs'
        paro.long_name = name
        paro.units = unit
        paro.set_auto_maskandscale(False)

        # Set the data variable
        paro[:,:,:] = Array

        # close the file
        time.sleep(1)
        nco.close()

        return()

    def Add_NC_Array_Static(nc_outname, Array, name, unit, Scaling_factor = 1):

        # create input array
        Array[np.isnan(Array)] = -9999 * np.float(Scaling_factor)
        Array = np.int_(Array * 1./np.float(Scaling_factor))

        # Create NetCDF file
        nco = netCDF4.Dataset(nc_outname, 'r+', format = 'NETCDF4_CLASSIC')
        nco.set_fill_on()

        paro = nco.createVariable('%s' %name, 'i',
                                       ('latitude', 'longitude'),fill_value=-9999,
                                        zlib=True, least_significant_digit=0)

        paro.scale_factor = Scaling_factor
        paro.add_offset = 0.00
        paro.grid_mapping = 'crs'
        paro.long_name = name
        paro.units = unit
        paro.set_auto_maskandscale(False)

        # Set the data variable
        paro[:,:] = Array

        # close the file
        time.sleep(1)
        nco.close()

        return()


    def Convert_dict_to_array(River_dict, Array_dict, Reference_data):


        if os.path.splitext(Reference_data)[-1] == '.nc':
            # Get raster information
            geo_out, proj, size_X, size_Y, size_Z, Time = Raster.Open_nc_info(Reference_data)
        else:
            # Get raster information
            geo_out, proj, size_X, size_Y = Raster.Open_array_info(Reference_data)

        # Create ID Matrix
        y,x = np.indices((size_Y, size_X))
        ID_Matrix = np.int32(np.ravel_multi_index(np.vstack((y.ravel(),x.ravel())),(size_Y,size_X),mode='clip').reshape(x.shape)) + 1

        # Get tiff array time dimension:
        time_dimension = int(np.shape(Array_dict[0])[0])

        # create an empty array
        DataCube = np.ones([time_dimension, size_Y, size_X]) * np.nan

        for river_part in range(0,len(River_dict)):
            for river_pixel in range(1,len(River_dict[river_part])):
                river_pixel_ID = River_dict[river_part][river_pixel]
                if len(np.argwhere(ID_Matrix == river_pixel_ID))>0:
                    row, col = np.argwhere(ID_Matrix == river_pixel_ID)[0][:]
                    DataCube[:,row,col] = Array_dict[river_part][:,river_pixel]

        return(DataCube)

    # def Run_command_window(argument):
    #     """
    #     This function runs the argument in the command window without showing cmd window

    #     Keyword Arguments:
    #     argument -- string, name of the adf file
    #     """
    #     if os.name == 'posix':
    #         argument = argument.replace(".exe","")
    #         os.system(argument)

    #     else:
    #         startupinfo = subprocess.STARTUPINFO()
    #         startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    #         process = subprocess.Popen(argument, startupinfo=startupinfo, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    #         process.wait()

    #     return()

    def Open_array_info(filename=''):
        """
        Opening a tiff info, for example size of array, projection and transform matrix.

        Keyword Arguments:
        filename -- 'C:/file/to/path/file.tif' or a gdal file (gdal.Open(filename))
            string that defines the input tiff file or gdal file

        """
        f = gdal.Open(r"%s" %filename)
        if f is None:
            print('%s does not exists' %filename)
        else:
            geo_out = f.GetGeoTransform()
            proj = f.GetProjection()
            size_X = f.RasterXSize
            size_Y = f.RasterYSize
            f = None
        return(geo_out, proj, size_X, size_Y)



    def Open_nc_info(NC_filename, Var = None):
        """
        Opening a nc info, for example size of array, time (ordinal), projection and transform matrix.

        Keyword Arguments:
        filename -- 'C:/file/to/path/file.nc'
            string that defines the input nc file

        """

        fh = netCDF4.Dataset(NC_filename, mode='r')

        if Var is None:
            Var = list(fh.variables.keys())[-1]

        data = fh.variables[Var][:]

        size_Y, size_X = np.int_(data.shape[-2:])
        if len(data.shape) == 3:
            size_Z = np.int_(data.shape[0])
            Time = fh.variables['time'][:]
        else:
            size_Z = 1
            Time = -9999
        lats = fh.variables['latitude'][:]
        lons = fh.variables['longitude'][:]

        Geo6 = fh.variables['latitude'].pixel_size
        Geo2 = fh.variables['longitude'].pixel_size
        Geo4 = np.max(lats) + Geo6/2
        Geo1 = np.min(lons) - Geo2/2

        crso = fh.variables['crs']
        proj = crso.projection
        epsg = Raster.Get_epsg(proj, extension = 'GEOGCS')
        geo_out = tuple([Geo1, Geo2, 0, Geo4, 0, Geo6])
        fh.close()

        return(geo_out, epsg, size_X, size_Y, size_Z, Time)

    def Open_nc_array(NC_filename, Var = None, Startdate = '', Enddate = ''):
        """
        Opening a nc array.

        Keyword Arguments:
        filename -- 'C:/file/to/path/file.nc'
            string that defines the input nc file
        Var -- string
            Defines the band name that must be opened.
        Startdate -- "yyyy-mm-dd"
            Defines the startdate (default is from beginning of array)
        Enddate -- "yyyy-mm-dd"
            Defines the enddate (default is from end of array)
        """

        fh = netCDF4.Dataset(NC_filename, mode='r')
        if Var == None:
            Var = fh.variables.keys()[-1]

        if Startdate != '':
            Time = fh.variables['time'][:]
            Array_check_start = np.ones(np.shape(Time))
            Date = pd.Timestamp(Startdate)
            Startdate_ord = Date.toordinal()
            Array_check_start[Time >= Startdate_ord] = 0
            Start = np.sum(Array_check_start)
        else:
            Start = 0

        if Enddate != '':
            Time = fh.variables['time'][:]
            Array_check_end = np.zeros(np.shape(Time))
            Date = pd.Timestamp(Enddate)
            Enddate_ord = Date.toordinal()
            Array_check_end[Enddate_ord >= Time] = 1
            End = np.sum(Array_check_end)
        else:
            try:
                Time = fh.variables['time'][:]
                End = len(Time)
            except:
                End = ''

        if (Enddate != '' or Startdate != ''):
            Data = fh.variables[Var][int(Start):int(End), :, :]

        else:
            Data = fh.variables[Var][:]
        fh.close()

        Data = np.array(Data)
        try:
            Data[Data==-9999] = np.nan
        except:
            pass

        return(Data)

    def Open_bil_array(bil_filename, band = 1):
        """
        Opening a bil array.

        Keyword Arguments:
        bil_filename -- 'C:/file/to/path/file.bil'
            string that defines the input tiff file or gdal file
        band -- integer
            Defines the band of the tiff that must be opened.
        """
        gdal.GetDriverByName('EHdr').Register()
        img = gdal.Open(bil_filename)
        Data = img.GetRasterBand(band).ReadAsArray()

        return(Data)

    def Open_ncs_array(NC_Directory, Var, Startdate, Enddate):
        """
        Opening a nc array.

        Keyword Arguments:
        NC_Directory -- 'C:/file/to/path'
            string that defines the path to all the simulation nc files
        Var -- string
            Defines the band name that must be opened.
        Startdate -- "yyyy-mm-dd"
            Defines the startdate
        Enddate -- "yyyy-mm-dd"
            Defines the enddate
        """

        panda_start = pd.Timestamp(Startdate)
        panda_end = pd.Timestamp(Enddate)

        years = range(int(panda_start.year), int(panda_end.year)+1)
        Data_end = []
        for year in years:

            NC_filename = os.path.join(NC_Directory, "%d.nc" %year)

            if year == years[0]:
                Startdate_now = Startdate
            else:
                Startdate_now = "%d-01-01" %int(year)

            if year == years[-1]:
                Enddate_now = Enddate
            else:
                Enddate_now = "%d-12-31" %int(year)

            Data_now = Raster.Open_nc_array(NC_filename, Var, Startdate_now, Enddate_now)

            if year == years[0]:
                Data_end = Data_now
            else:
                Data_end = np.vstack([Data_end,Data_now])

        Data_end = np.array(Data_end)

        return(Data_end)

    def Open_nc_dict(input_netcdf, group_name, startdate = '', enddate = ''):
        """
        Opening a nc dictionary.

        Keyword Arguments:
        filename -- 'C:/file/to/path/file.nc'
            string that defines the input nc file
        group_name -- string
            Defines the group name that must be opened.
        Startdate -- "yyyy-mm-dd"
            Defines the startdate (default is from beginning of array)
        Enddate -- "yyyy-mm-dd"
            Defines the enddate (default is from end of array)
        """
        # sort out if the dataset is static or dynamic (written in group_name)
        kind_of_data = group_name.split('_')[-1]

        # if it is dynamic also collect the time parameter
        if kind_of_data == 'dynamic':
            time_dates = Raster.Open_nc_array(input_netcdf, Var = 'time')
            Amount_months = len(time_dates)

        # Open the input netcdf and the wanted group name
        in_nc = netCDF4.Dataset(input_netcdf)
        data = in_nc.groups[group_name]

        # Convert the string into a string that can be retransformed into a dictionary
        string_dict = str(data)
        split_dict = str(string_dict.split('\n')[2:-4])
        split_dict = split_dict.replace("'","")
        split_dict = split_dict[1:-1]
        dictionary = dict()
        split_dict_split = re.split(':|,  ',split_dict)

        # Loop over every attribute and add the array
        for i in range(0,len(split_dict_split)):
            number_val = split_dict_split[i]
            if i % 2 == 0:
                Array_text = split_dict_split[i + 1].replace(",","")
                Array_text = Array_text.replace("[","")
                Array_text = Array_text.replace("]","")
                # If the array is dynamic add a 2D array
                if kind_of_data == 'dynamic':
                    tot_length = len(np.fromstring(Array_text,sep = ' '))
                    dictionary[int(number_val)] = np.fromstring(Array_text,sep = ' ').reshape((int(Amount_months), int(tot_length/Amount_months)))
                # If the array is static add a 1D array
                else:
                    dictionary[int(number_val)] = np.fromstring(Array_text,sep = ' ')

        # Clip the dynamic dataset if a start and enddate is defined
        if kind_of_data == 'dynamic':

            if startdate != '':
                Array_check_start = np.ones(np.shape(time_dates))
                Date = pd.Timestamp(startdate)
                Startdate_ord = Date.toordinal()
                Array_check_start[time_dates >= Startdate_ord] = 0
                Start = np.sum(Array_check_start)
            else:
                Start = 0

            if enddate != '':
                Array_check_end = np.zeros(np.shape(time_dates))
                Date = pd.Timestamp(enddate)
                Enddate_ord = Date.toordinal()
                Array_check_end[Enddate_ord >= time_dates] = 1
                End = np.sum(Array_check_end)
            else:
                try:
                    time_dates = in_nc.variables['time'][:]
                    End = len(time_dates)
                except:
                    End = ''

            if Start != 0 or (End != len(time_dates) or ''):

                if End == '':
                    End = len(time_dates)

                for key in dictionary.iterkeys():

                    Array = dictionary[key][:,:]
                    Array_new = Array[int(Start):int(End),:]
                    dictionary[key] = Array_new
        in_nc.close()

        return(dictionary)

    def Clip_Dataset_GDAL(input_name, output_name, latlim, lonlim):
        """
        Clip the data to the defined extend of the user (latlim, lonlim) by using the gdal_translate executable of gdal.

        Keyword Arguments:
        input_name -- input data, input directory and filename of the tiff file
        output_name -- output data, output filename of the clipped file
        latlim -- [ymin, ymax]
        lonlim -- [xmin, xmax]
        """
        # Get environmental variable
        WA_env_paths = os.environ["WA_PATHS"].split(';')
        GDAL_env_path = WA_env_paths[0]
        GDALTRANSLATE_PATH = os.path.join(GDAL_env_path, 'gdal_translate.exe')

        # find path to the executable
        fullCmd = ' '.join(["%s" %(GDALTRANSLATE_PATH), '-projwin %s %s %s %s -of GTiff %s %s'  %(lonlim[0], latlim[1], lonlim[1], latlim[0], input_name, output_name)])
        Raster.Run_command_window(fullCmd)

        return()

    def clip_data(input_file, latlim, lonlim):
        """
        Clip the data to the defined extend of the user (latlim, lonlim) or to the
        extend of the DEM tile

        Keyword Arguments:
        input_file -- output data, output of the clipped dataset
        latlim -- [ymin, ymax]
        lonlim -- [xmin, xmax]
        """
        try:
            if input_file.split('.')[-1] == 'tif':
                dest_in = gdal.Open(input_file)
            else:
                dest_in = input_file
        except:
            dest_in = input_file

        # Open Array
        data_in = dest_in.GetRasterBand(1).ReadAsArray()

        # Define the array that must remain
        Geo_in = dest_in.GetGeoTransform()
        Geo_in = list(Geo_in)
        Start_x = np.max([int(np.floor(((lonlim[0]) - Geo_in[0])/ Geo_in[1])),0])
        End_x = np.min([int(np.ceil(((lonlim[1]) - Geo_in[0])/ Geo_in[1])),int(dest_in.RasterXSize)])

        Start_y = np.max([int(np.floor((Geo_in[3] - latlim[1])/ -Geo_in[5])),0])
        End_y = np.min([int(np.ceil(((latlim[0]) - Geo_in[3])/Geo_in[5])), int(dest_in.RasterYSize)])

        #Create new GeoTransform
        Geo_in[0] = Geo_in[0] + Start_x * Geo_in[1]
        Geo_in[3] = Geo_in[3] + Start_y * Geo_in[5]
        Geo_out = tuple(Geo_in)

        data = np.zeros([End_y - Start_y, End_x - Start_x])

        data = data_in[Start_y:End_y,Start_x:End_x]
        dest_in = None

        return(data, Geo_out)

    def reproject_dataset_epsg(dataset, pixel_spacing, epsg_to, method = 2):
        """
        A sample function to reproject and resample a GDAL dataset from within
        Python. The idea here is to reproject from one system to another, as well
        as to change the pixel size. The procedure is slightly long-winded, but
        goes like this:

        1. Set up the two Spatial Reference systems.
        2. Open the original dataset, and get the geotransform
        3. Calculate bounds of new geotransform by projecting the UL corners
        4. Calculate the number of pixels with the new projection & spacing
        5. Create an in-memory raster dataset
        6. Perform the projection

        Keywords arguments:
        dataset -- 'C:/file/to/path/file.tif'
            string that defines the input tiff file
        pixel_spacing -- float
            Defines the pixel size of the output file
        epsg_to -- integer
             The EPSG code of the output dataset
        method -- 1,2,3,4 default = 2
            1 = Nearest Neighbour, 2 = Bilinear, 3 = lanzcos, 4 = average
        """

        # 1) Open the dataset
        g = gdal.Open(dataset)
        if g is None:
            print('input folder does not exist')

        # Get EPSG code
        epsg_from = Raster.Get_epsg(g)

        # Get the Geotransform vector:
        geo_t = g.GetGeoTransform()
        # Vector components:
        # 0- The Upper Left easting coordinate (i.e., horizontal)
        # 1- The E-W pixel spacing
        # 2- The rotation (0 degrees if image is "North Up")
        # 3- The Upper left northing coordinate (i.e., vertical)
        # 4- The rotation (0 degrees)
        # 5- The N-S pixel spacing, negative as it is counted from the UL corner
        x_size = g.RasterXSize  # Raster xsize
        y_size = g.RasterYSize  # Raster ysize

        epsg_to = int(epsg_to)

        # 2) Define the UK OSNG, see <http://spatialreference.org/ref/epsg/27700/>
        osng = osr.SpatialReference()
        osng.ImportFromEPSG(epsg_to)
        wgs84 = osr.SpatialReference()
        wgs84.ImportFromEPSG(epsg_from)

        inProj = Proj(init='epsg:%d' %epsg_from)
        outProj = Proj(init='epsg:%d' %epsg_to)

        # Up to here, all  the projection have been defined, as well as a
        # transformation from the from to the to
        ulx, uly = transform(inProj,outProj,geo_t[0], geo_t[3])
        lrx, lry = transform(inProj,outProj,geo_t[0] + geo_t[1] * x_size,
                                            geo_t[3] + geo_t[5] * y_size)

        # See how using 27700 and WGS84 introduces a z-value!
        # Now, we create an in-memory raster
        mem_drv = gdal.GetDriverByName('MEM')

        # The size of the raster is given the new projection and pixel spacing
        # Using the values we calculated above. Also, setting it to store one band
        # and to use Float32 data type.
        col = int((lrx - ulx)/pixel_spacing)
        rows = int((uly - lry)/pixel_spacing)

        # Re-define lr coordinates based on whole number or rows and columns
        (lrx, lry) = (ulx + col * pixel_spacing, uly -
                      rows * pixel_spacing)

        dest = mem_drv.Create('', col, rows, 1, gdal.GDT_Float32)
        if dest is None:
            print('input folder to large for memory, clip input map')

       # Calculate the new geotransform
        new_geo = (ulx, pixel_spacing, geo_t[2], uly,
                   geo_t[4], - pixel_spacing)

        # Set the geotransform
        dest.SetGeoTransform(new_geo)
        dest.SetProjection(osng.ExportToWkt())

        # Perform the projection/resampling
        if method == 1:
            gdal.ReprojectImage(g, dest, wgs84.ExportToWkt(), osng.ExportToWkt(),gdal.GRA_NearestNeighbour)
        if method == 2:
            gdal.ReprojectImage(g, dest, wgs84.ExportToWkt(), osng.ExportToWkt(),gdal.GRA_Bilinear)
        if method == 3:
            gdal.ReprojectImage(g, dest, wgs84.ExportToWkt(), osng.ExportToWkt(), gdal.GRA_Lanczos)
        if method == 4:
            gdal.ReprojectImage(g, dest, wgs84.ExportToWkt(), osng.ExportToWkt(), gdal.GRA_Average)
        return dest, ulx, lry, lrx, uly, epsg_to

    def reproject_MODIS(input_name, epsg_to):
        '''
        Reproject the merged data file by using gdalwarp. The input projection must be the MODIS projection.
        The output projection can be defined by the user.

        Keywords arguments:
        input_name -- 'C:/file/to/path/file.tif'
            string that defines the input tiff file
        epsg_to -- integer
            The EPSG code of the output dataset
        '''
        # Define the output name
        name_out = ''.join(input_name.split(".")[:-1]) + '_reprojected.tif'

        # Get environmental variable
        WA_env_paths = os.environ["WA_PATHS"].split(';')
        GDAL_env_path = WA_env_paths[0]
        GDALWARP_PATH = os.path.join(GDAL_env_path, 'gdalwarp.exe')

        # find path to the executable
        fullCmd = ' '.join(["%s" %(GDALWARP_PATH), '-overwrite -s_srs "+proj=sinu +lon_0=0 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=m +no_defs"', '-t_srs EPSG:%s -of GTiff' %(epsg_to), input_name, name_out])
        Raster.Run_command_window(fullCmd)

        return(name_out)

    def reproject_dataset_example(dataset, dataset_example, method=1):
        """
        A sample function to reproject and resample a GDAL dataset from within
        Python. The user can define the wanted projection and shape by defining an example dataset.

        Keywords arguments:
        dataset -- 'C:/file/to/path/file.tif' or a gdal file (gdal.Open(filename))
            string that defines the input tiff file or gdal file
        dataset_example -- 'C:/file/to/path/file.tif' or a gdal file (gdal.Open(filename))
            string that defines the input tiff file or gdal file
        method -- 1,2,3,4 default = 1
            1 = Nearest Neighbour, 2 = Bilinear, 3 = lanzcos, 4 = average
        """
        # open dataset that must be transformed
        try:
            if os.path.splitext(dataset)[-1] == '.tif':
                g = gdal.Open(dataset)
            else:
                g = dataset
        except:
                g = dataset
        epsg_from = Raster.Get_epsg(g)

        #exceptions
        if epsg_from == 9001:
            epsg_from = 5070

        # open dataset that is used for transforming the dataset
        try:
            if os.path.splitext(dataset_example)[-1] == '.tif':
                gland = gdal.Open(dataset_example)
                epsg_to = Raster.Get_epsg(gland)
            elif os.path.splitext(dataset_example)[-1] == '.nc':

                geo_out, epsg_to, size_X, size_Y, size_Z, Time = Raster.Open_nc_info(dataset_example)
                data = np.zeros([size_Y, size_X])
                gland = Raster.CreateRaster(data, geo_out, str(epsg_to))
            else:
                gland = dataset_example
                epsg_to = Raster.Get_epsg(gland)
        except:
                gland = dataset_example
                epsg_to = Raster.Get_epsg(gland)

        # Set the EPSG codes
        osng = osr.SpatialReference()
        osng.ImportFromEPSG(epsg_to)
        wgs84 = osr.SpatialReference()
        wgs84.ImportFromEPSG(epsg_from)

        # Get shape and geo transform from example
        geo_land = gland.GetGeoTransform()
        col=gland.RasterXSize
        rows=gland.RasterYSize

        # Create new raster
        mem_drv = gdal.GetDriverByName('MEM')
        dest1 = mem_drv.Create('', col, rows, 1, gdal.GDT_Float32)
        dest1.SetGeoTransform(geo_land)
        dest1.SetProjection(osng.ExportToWkt())

        # Perform the projection/resampling
        if method == 1:
            gdal.ReprojectImage(g, dest1, wgs84.ExportToWkt(), osng.ExportToWkt(), gdal.GRA_NearestNeighbour)
        if method == 2:
            gdal.ReprojectImage(g, dest1, wgs84.ExportToWkt(), osng.ExportToWkt(), gdal.GRA_Bilinear)
        if method == 3:
            gdal.ReprojectImage(g, dest1, wgs84.ExportToWkt(), osng.ExportToWkt(), gdal.GRA_Lanczos)
        if method == 4:
            gdal.ReprojectImage(g, dest1, wgs84.ExportToWkt(), osng.ExportToWkt(), gdal.GRA_Average)
        return(dest1)

    def resize_array_example(Array_in, Array_example, method=1):
        """
        This function resizes an array so it has the same size as an example array
        The extend of the array must be the same

        Keyword arguments:
        Array_in -- []
            Array: 2D or 3D array
        Array_example -- []
            Array: 2D or 3D array
        method: -- 1 ... 5
            int: Resampling method
        """

        # Create old raster
        Array_out_shape = np.int_(Array_in.shape)
        Array_out_shape[-1] = Array_example.shape[-1]
        Array_out_shape[-2] = Array_example.shape[-2]

        if method == 1:
            interpolation_method='nearest'
            interpolation_number = 0
        if method == 2:
            interpolation_method='bicubic'
            interpolation_number = 3
        if method == 3:
            interpolation_method='bilinear'
            interpolation_number = 1
        if method == 4:
            interpolation_method='cubic'
        if method == 5:
            interpolation_method='lanczos'

        if len(Array_out_shape) == 3:
            Array_out = np.zeros(Array_out_shape)

            for i in range(0, Array_out_shape[0]):
                Array_in_slice = Array_in[i,:,:]
                size=tuple(Array_out_shape[1:])

                if sys.version_info[0] == 2:

                    Array_out_slice = misc.imresize(np.float_(Array_in_slice), size, interp=interpolation_method, mode='F')
                if sys.version_info[0] == 3:
                    import skimage.transform as transform
                    Array_out_slice= transform.resize(np.float_(Array_in_slice), size, order=interpolation_number)

                Array_out[i,:,:] = Array_out_slice

        elif len(Array_out_shape) == 2:

            size=tuple(Array_out_shape)
            if sys.version_info[0] == 2:

                Array_out= misc.imresize(np.float_(Array_in), size, interp=interpolation_method, mode='F')
            if sys.version_info[0] == 3:
                import skimage.transform as transform
                Array_out= transform.resize(np.float_(Array_in), size, order=interpolation_number)

        else:
            print('only 2D or 3D dimensions are supported')

        return(Array_out)

    def Get_epsg(g, extension = 'tiff'):
        """
        This function reads the projection of a GEOGCS file or tiff file

        Keyword arguments:
        g -- string
            Filename to the file that must be read
        extension -- tiff or GEOGCS
            Define the extension of the dataset (default is tiff)
        """
        try:
            if extension == 'tiff':
                # Get info of the dataset that is used for transforming
                g_proj = g.GetProjection()
                Projection=g_proj.split('EPSG","')
            if extension == 'GEOGCS':
                Projection = g
            epsg_to=int((str(Projection[-1]).split(']')[0])[0:-1])
        except:
           epsg_to=4326
           #print 'Was not able to get the projection, so WGS84 is assumed'
        return(epsg_to)

    def gap_filling(dataset,NoDataValue, method = 1):
        """
        This function fills the no data gaps in a numpy array

        Keyword arguments:
        dataset -- 'C:/'  path to the source data (dataset that must be filled)
        NoDataValue -- Value that must be filled
        """


        try:
            if dataset.split('.')[-1] == 'tif':
                # Open the numpy array
                data = Raster.GetRasterData(dataset)
                Save_as_tiff = 1
            else:
                data = dataset
                Save_as_tiff = 0
        except:
            data = dataset
            Save_as_tiff = 0

        # fill the no data values
        if NoDataValue is np.nan:
            mask = ~(np.isnan(data))
        else:
            mask = ~(data==NoDataValue)
        xx, yy = np.meshgrid(np.arange(data.shape[1]), np.arange(data.shape[0]))
        xym = np.vstack( (np.ravel(xx[mask]), np.ravel(yy[mask])) ).T
        data0 = np.ravel( data[:,:][mask] )

        if method == 1:
            interp0 = scipy.interpolate.NearestNDInterpolator( xym, data0 )
            data_end = interp0(np.ravel(xx), np.ravel(yy)).reshape( xx.shape )

        if method == 2:
            interp0 = scipy.interpolate.LinearNDInterpolator( xym, data0 )
            data_end = interp0(np.ravel(xx), np.ravel(yy)).reshape( xx.shape )

        if Save_as_tiff == 1:
            EndProduct=dataset[:-4] + '_GF.tif'

            # collect the geoinformation
            geo_out, proj, size_X, size_Y = Raster.Open_array_info(dataset)

            # Save the filled array as geotiff
            Raster.CreateRaster(name=EndProduct, data=data_end, geo=geo_out, projection=proj)

        else:
            EndProduct = data_end

        return (EndProduct)

    # def Get3Darray_time_series_monthly(Data_Path, Startdate, Enddate, Example_data = None):
    #     """
    #     This function creates a datacube

    #     Keyword arguments:
    #     Data_Path -- 'product/monthly'
    #         str: Path to the dataset
    #     Startdate -- 'YYYY-mm-dd'
    #         str: startdate of the 3D array
    #     Enddate -- 'YYYY-mm-dd'
    #         str: enddate of the 3D array
    #     Example_data: -- 'C:/....../.tif'
    #         str: Path to an example tiff file (all arrays will be reprojected to this example)
    #     """

    #     # Get a list of dates that needs to be reprojected
    #     Dates = pd.date_range(Startdate, Enddate, freq = 'MS')

    #     # Change Working directory
    #     os.chdir(Data_Path)
    #     i = 0

    #     # Loop over the months
    #     for Date in Dates:

    #         # Create the end monthly file name
    #         End_tiff_file_name = 'monthly_%d.%02d.01.tif' %(Date.year, Date.month)

    #         # Search for this file in directory
    #         file_name = glob.glob('*%s' %End_tiff_file_name)

    #         # Select the first file that is found
    #         file_name_path = os.path.join(Data_Path, file_name[0])

    #         # Check if an example file is selected
    #         if Example_data != None:

    #             # If it is the first day set the example gland file
    #             if Date == Dates[0]:

    #                 # Check the format to read general info

    #                 # if Tiff
    #                 if os.path.splitext(Example_data)[-1] == '.tif':
    #                     geo_out, proj, size_X, size_Y = Raster.Open_array_info(Example_data)
    #                     dataTot=np.zeros([len(Dates),size_Y,size_X])

    #                 # if netCDF
    #                 if os.path.splitext(Example_data)[-1] == '.nc':
    #                     geo_out, projection, size_X, size_Y, size_Z, Time = Raster.Open_nc_info(Example_data)
    #                     dataTot=np.zeros([len(Dates),size_Y,size_X])

    #                     # Create memory file for reprojection
    #                     data = Raster.Open_nc_array(Example_data, "Landuse")
    #                     driver = gdal.GetDriverByName("MEM")
    #                     gland = driver.Create('', int(size_X), int(size_Y), 1,
    #                                            gdal.GDT_Float32)
    #                     srse = osr.SpatialReference()
    #                     if projection == '' or projection == 4326:
    #                         srse.SetWellKnownGeogCS("WGS84")
    #                     else:
    #                         srse.SetWellKnownGeogCS(projection)
    #                     gland.SetProjection(srse.ExportToWkt())
    #                     gland.GetRasterBand(1).SetNoDataValue(-9999)
    #                     gland.SetGeoTransform(geo_out)
    #                     gland.GetRasterBand(1).WriteArray(data)

    #                 # use the input parameter as it is already an example file
    #                 else:
    #                     gland = Example_data

    #             # reproject dataset
    #             dest = Raster.reproject_dataset_example(file_name_path, gland, method = 4)
    #             Array_one_date = dest.GetRasterBand(1).ReadAsArray()

    #         # if there is no example dataset defined
    #         else:

    #             # Get the properties from the first file
    #             if Date is Dates[0]:
    #                     geo_out, proj, size_X, size_Y = Raster.Open_array_info(file_name_path)
    #                     dataTot=np.zeros([len(Dates),size_Y,size_X])
    #             Array_one_date = Raster.GetRasterData(file_name_path)

    #         # Create the 3D array
    #         dataTot[i,:,:] = Array_one_date
    #         i += 1

    #     return(dataTot)

    def Vector_to_Raster(Dir, shapefile_name, reference_raster_data_name):
        """
        This function creates a raster of a shp file

        Keyword arguments:
        Dir --
            str: path to the basin folder
        shapefile_name -- 'C:/....../.shp'
            str: Path from the shape file
        reference_raster_data_name -- 'C:/....../.tif'
            str: Path to an example tiff file (all arrays will be reprojected to this example)
        """



        geo, proj, size_X, size_Y = Raster.Open_array_info(reference_raster_data_name)

        x_min = geo[0]
        x_max = geo[0] + size_X * geo[1]
        y_min = geo[3] + size_Y * geo[5]
        y_max = geo[3]
        pixel_size = geo[1]

        # Filename of the raster Tiff that will be created
        Dir_Basin_Shape = os.path.join(Dir,'Basin')
        if not os.path.exists(Dir_Basin_Shape):
            os.mkdir(Dir_Basin_Shape)

        Basename = os.path.basename(shapefile_name)
        Dir_Raster_end = os.path.join(Dir_Basin_Shape, os.path.splitext(Basename)[0]+'.tif')

        # Open the data source and read in the extent
        source_ds = ogr.Open(shapefile_name)
        source_layer = source_ds.GetLayer()

        # Create the destination data source
        x_res = int(round((x_max - x_min) / pixel_size))
        y_res = int(round((y_max - y_min) / pixel_size))

        # Create tiff file
        target_ds = gdal.GetDriverByName('GTiff').Create(Dir_Raster_end, x_res, y_res, 1, gdal.GDT_Float32, ['COMPRESS=LZW'])
        target_ds.SetGeoTransform(geo)
        srse = osr.SpatialReference()
        srse.SetWellKnownGeogCS(proj)
        target_ds.SetProjection(srse.ExportToWkt())
        band = target_ds.GetRasterBand(1)
        target_ds.GetRasterBand(1).SetNoDataValue(-9999)
        band.Fill(-9999)

        # Rasterize the shape and save it as band in tiff file
        gdal.RasterizeLayer(target_ds, [1], source_layer, None, None, [1], ['ALL_TOUCHED=TRUE'])
        target_ds = None

        # Open array
        Raster_Basin = Raster.GetRasterData(Dir_Raster_end)

        return(Raster_Basin)

    def Moving_average(dataset, Moving_front, Moving_back):
        """
        This function applies the moving averages over a 3D matrix called dataset.

        Keyword Arguments:
        dataset -- 3D matrix [time, ysize, xsize]
        Moving_front -- Amount of time steps that must be considered in the front of the current month
        Moving_back -- Amount of time steps that must be considered in the back of the current month
        """

        dataset_out = np.zeros((int(np.shape(dataset)[0]) - Moving_back - Moving_front, int(np.shape(dataset)[1]), int(np.shape(dataset)[2])))

        for i in range(Moving_back, (int(np.shape(dataset)[0]) - Moving_front)):
            dataset_out[i - Moving_back,:,:] = np.nanmean(dataset[i - Moving_back : i + 1 + Moving_front, :,:], 0)

        return(dataset_out)

    def Get_ordinal(Startdate, Enddate, freq = 'MS'):
        """
        This function creates an array with ordinal time.

        Keyword Arguments:
        Startdate -- Startdate of the ordinal time
        Enddate -- Enddate of the ordinal time
        freq -- Time frequencies between start and enddate
        """


        Dates = pd.date_range(Startdate, Enddate, freq = freq)
        i = 0
        ordinal = np.zeros([len(Dates)])
        for date in Dates:

            p = dt.date(date.year, date.month, date.day).toordinal()
            ordinal[i]=p
            i += 1

        return(ordinal)

    # def Create_Buffer(Data_In, Buffer_area):

    #    '''
    #    This function creates a 3D array which is used to apply the moving window
    #    '''

    #    # Buffer_area = 2 # A block of 2 times Buffer_area + 1 will be 1 if there is the pixel in the middle is 1
    #    Data_Out=np.empty((len(Data_In),len(Data_In[1])))
    #    Data_Out[:,:] = Data_In
    #    for ypixel in range(0,Buffer_area + 1):

    #         for xpixel in range(1,Buffer_area + 1):

    #            if ypixel==0:
    #                 for xpixel in range(1,Buffer_area + 1):
    #                     Data_Out[:,0:-xpixel] += Data_In[:,xpixel:]
    #                     Data_Out[:,xpixel:] += Data_In[:,:-xpixel]

    #                 for ypixel in range(1,Buffer_area + 1):

    #                     Data_Out[ypixel:,:] += Data_In[:-ypixel,:]
    #                     Data_Out[0:-ypixel,:] += Data_In[ypixel:,:]

    #            else:
    #                Data_Out[0:-xpixel,ypixel:] += Data_In[xpixel:,:-ypixel]
    #                Data_Out[xpixel:,ypixel:] += Data_In[:-xpixel,:-ypixel]
    #                Data_Out[0:-xpixel,0:-ypixel] += Data_In[xpixel:,ypixel:]
    #                Data_Out[xpixel:,0:-ypixel] += Data_In[:-xpixel,ypixel:]

    #    Data_Out[Data_Out>0.1] = 1
    #    Data_Out[Data_Out<=0.1] = 0

    #    return(Data_Out)

    def ListAttributes(self):
        """
        Print Attributes List
        """

        print('\n')
        print('Attributes List of: ' + repr(self.__dict__['name']) + ' - ' + self.__class__.__name__ + ' Instance\n')
        self_keys = list(self.__dict__.keys())
        self_keys.sort()
        for key in self_keys:
            if key != 'name':
                print(str(key) + ' : ' + repr(self.__dict__[key]))

        print('\n')