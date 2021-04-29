def get_cumul_return(vector):
    result = list()
    for ele in vector:
        result.append((ele - vector[0]) / vector[0])

    return result