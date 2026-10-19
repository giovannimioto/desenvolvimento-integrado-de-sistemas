#include <iostream>
#include <Eigen/Dense>

int main() {
    Eigen::MatrixXd a = Eigen::MatrixXd::Random(3, 3);
    std::cout << a << std::endl;
    return 0;
}