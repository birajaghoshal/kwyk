#!/usr/bin/env python3

from pathlib import Path
import nibabel as nib
import numpy as np
from nobrainer.volume import normalize_zero_one
from nobrainer.volume import replace
from nobrainer.io import read_mapping
from nobrainer.metrics import dice_numpy
from nobrainer.predict import predict as _predict
DT_X = "float32"


def validate_from_filepath(filepath,
                          predictor,
                          block_shape,
                          n_classes,
                          mapping_y,
                          returnVariance=False,
                          returnEntropy=False,
                          returnArrayFromImages=False, 
                          n_samples=1,
                          normalizer=normalize_zero_one,
                          batch_size=4,
                          dtype=DT_X,
                          ):
    """Computes dice for a prediction compared to a ground truth image.

    Args:
        filepath: tuple, tupel of paths to existing neuroimaging volume (index 0)
         and ground truth (index 1).
        predictor: TensorFlow Predictor object, predictor from previously
            trained model.
        n_classes: int, number of classifications the model is trained to output.
        mapping_y: path-like, path to csv mapping file per command line argument.
        block_shape: tuple of len 3, shape of blocks on which to predict.
        returnVariance: Boolean. If set True, it returns the running population 
            variance along with mean. Note, if the n_samples is smaller or equal to 1,
            the variance will not be returned; instead it will return None
        returnEntropy: Boolean. If set True, it returns the running entropy.
            along with mean.       
        returnArrayFromImages: Boolean. If set True and the given input is either image,
            filepath, or filepaths, it will return arrays of [mean, variance, entropy]
            instead of images of them. Also, if the input is array, it will
            simply return array, whether or not this flag is True or False.
        n_samples: The number of sampling. If set as 1, it will just return the 
            single prediction value.
        normalizer: callable, function that accepts an ndarray and returns an
            ndarray. Called before separating volume into blocks.
        batch_size: int, number of sub-volumes per batch for prediction.
        dtype: str or dtype object, dtype of features.

    Returns:
        `nibabel.spatialimages.SpatialImage` or arrays of predictions of 
        mean, variance(optional), and entropy (optional).
    """
    if not Path(filepath).is_file():
        raise FileNotFoundError("could not find file {}".format(filepath[0]))
    img = nib.load(filepath[0])
    y = nib.load(filepath[1])

    outputs = _predict(
        img=img,
        predictor=predictor,
        block_shape=block_shape,
        returnVariance=returnVariance,
        returnEntropy=returnEntropy,
        returnArrayFromImages=returnArrayFromImages, 
        n_samples=n_samples,
        normalizer=normalizer,
        batch_size=batch_size)
    prediction_image = outputs[0]

    y = replace(y, read_mapping(mapping_y))
    dice = np.zeros(n_classes)
    for i in range(n_classes):
        u = np.equal(prediction_image,i)
        v = np.equal(y,i)
        dice[i]= dice_numpy(u,v)

    return outputs, dice






def validate_from_filepaths(filepaths,
                          predictor,
                          block_shape,
                          n_classes,
                          mapping_y,
                          returnVariance=False,
                          returnEntropy=False,
                          returnArrayFromImages=False, 
                          n_samples=1,
                          normalizer=normalize_zero_one,
                          batch_size=4,
                          dtype=DT_X,
                          ):
    """Yield predictions from filepaths using a SavedModel.

    Args:
        filepaths: list, neuroimaging volume filepaths on which to predict.
        n_classes: int, number of classifications the model is trained to output.
        mapping_y: path-like, path to csv mapping file per command line argument.
        block_shape: tuple of len 3, shape of blocks on which to predict.
        predictor: TensorFlow Predictor object, predictor from previously
            trained model.
        block_shape: tuple of len 3, shape of blocks on which to predict.
        normalizer: callable, function that accepts an ndarray and returns
            an ndarray. Called before separating volume into blocks.
        batch_size: int, number of sub-volumes per batch for prediction.
        dtype: str or dtype object, dtype of features.

    Returns:
        None
    """
    for filepath in filepaths:

        outputs,dice = validate_from_filepath(
            filepath=filepath,
            predictor=predictor,
            n_classes = n_classes,
            mapping_y = mapping_y,
            block_shape=block_shape,
            returnVariance=returnVariance,
            returnEntropy=returnEntropy,
            returnArrayFromImages=returnArrayFromImages, 
            n_samples=n_samples,
            normalizer=normalizer,
            batch_size=batch_size,
            dtype=dtype)


        outpath = Path(filepath[0])
        suffixes = '.'.join(s for s in outpath.suffixes)
        meanPath = outpath.parent / (outpath.stem + '_mean.' + suffixes)
        variancePath = outpath.parent / (outpath.stem + '_variance.' + suffixes)
        entropyPath = outpath.parent / (outpath.stem + '_entropy.' + suffixes)
        dicePath = outpath.parent / (outpath.stem + '_dice.npy')
        if meanPath.is_file() or variancePath.is_file() or entropyPath.is_file():
            raise Exception(str(meanPath) + " or " + str(variancePath) + " or " + str(entropyPath) + " already exists.")

        nib.save(outputs[0], meanPath) # fix
        if not returnArrayFromImages:
            includeVariance = ((n_samples > 1) and (returnVariance))
            returnEntropy = returnEntropy
            if includeVariance and returnEntropy:
                nib.save(outputs[1], str(variancePath))
                nib.save(outputs[2], str(entropyPath))
            elif includeVariance:
                nib.save(outputs[1], str(variancePath))
            else:
                nib.save(outputs[1], str(entropyPath))

    print(filepath[0])
    print('Dice: ' + str(np.mean(dice)))
    np.save(dicePath,dice)








